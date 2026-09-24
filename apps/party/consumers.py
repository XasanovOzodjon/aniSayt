from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from . import presence, services


class PartyConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return
        self.code = self.scope['url_route']['kwargs']['code']
        self.group = f'party_{self.code}'
        self.user_group = f'party_{self.code}_u_{user.pk}'
        self.user_id = user.pk
        try:
            party = await database_sync_to_async(services.get_open)(self.code)
        except services.PartyError:
            await self.close(code=4404)
            return
        if await database_sync_to_async(presence.is_full)(self.code, user.pk):
            await self.close(code=4403)
            return
        you = services.member_payload(user, host_id=party.host_id)
        you['_ch'] = self.channel_name
        await database_sync_to_async(presence.remember)(self.code, you)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()
        self.joined = True
        hello = await database_sync_to_async(self._hello)(party, you)
        await self.send_json(hello)
        await self.group_send_event({
            'type': 'member-join',
            'member': presence._public(you),
            'members': hello['members'],
        })

    async def disconnect(self, code):
        if not getattr(self, 'code', None):
            return
        if getattr(self, 'user_id', None):
            await database_sync_to_async(presence.forget)(
                self.code, self.user_id, self.channel_name,
            )
        if getattr(self, 'group', None):
            await self.channel_layer.group_discard(self.group, self.channel_name)
            await self.channel_layer.group_discard(self.user_group, self.channel_name)
        if not getattr(self, 'joined', False):
            return
        try:
            left = await database_sync_to_async(self._after_leave)()
            await self.group_send_event({
                'type': 'member-leave',
                'user_id': self.user_id,
                'members': left['members'],
                'party': left['party'],
            })
        except services.PartyError:
            pass

    async def receive_json(self, content, **kwargs):
        kind = content.get('type')
        if kind == 'ping':
            await self._pong()
        elif kind in ('play', 'pause', 'seek'):
            await self._transport(kind, content.get('position'))
        elif kind == 'buffering':
            await self._buffer(True)
        elif kind == 'ready':
            await self._buffer(False)
        elif kind == 'chat':
            await self._chat(content.get('body') or '')
        elif kind == 'control':
            await self._control(content.get('mode'))
        elif kind == 'signal':
            await self._signal(content)
        elif kind == 'camera':
            mic = content.get('mic')
            await self._camera(bool(content.get('on')), None if mic is None else bool(mic))

    async def party_event(self, event):
        await self.send_json(event['payload'])

    async def group_send_event(self, payload):
        await self.channel_layer.group_send(self.group, {
            'type': 'party.event',
            'payload': payload,
        })

    def _hello(self, party, you):
        return {
            'type': 'hello',
            'party': services.party_payload(party),
            'you': presence._public(you),
            'members': presence.members(self.code),
            'messages': services.recent_messages(party),
            'ice': services.ice_servers(),
        }

    def _after_leave(self):
        party = services.sync_after_leave(services.get_open(self.code))
        return {
            'party': services.party_payload(party),
            'members': presence.members(self.code),
        }

    async def _pong(self):
        try:
            party = await database_sync_to_async(services.get_open)(self.code)
        except services.PartyError as exc:
            if exc.status == 410:
                await self.send_json({'type': 'closed', 'party': {'code': self.code, 'closed': True}})
                await self.close(code=4404)
                return
            await self.send_json({'type': 'error', 'message': exc.message})
            return
        await self.send_json({
            'type': 'pong',
            'party': await database_sync_to_async(services.party_payload)(party),
        })

    async def _transport(self, action, position):
        try:
            party = await database_sync_to_async(self._do_transport)(action, position)
        except services.PartyError as exc:
            await self.send_json({'type': 'error', 'message': exc.message})
            return
        await self.group_send_event({
            'type': 'state',
            'party': await database_sync_to_async(services.party_payload)(party),
            'by': self.user_id,
        })

    def _do_transport(self, action, position):
        party = services.get_open(self.code)
        return services.apply_transport(party, self.scope['user'], action, position)

    async def _buffer(self, waiting):
        try:
            party = await database_sync_to_async(self._do_buffer)(waiting)
        except services.PartyError as exc:
            await self.send_json({'type': 'error', 'message': exc.message})
            return
        await self.group_send_event({
            'type': 'state',
            'party': await database_sync_to_async(services.party_payload)(party),
            'by': self.user_id,
        })

    def _do_buffer(self, waiting):
        party = services.get_open(self.code)
        return services.set_buffering(party, self.scope['user'], waiting)

    async def _chat(self, body):
        try:
            message = await database_sync_to_async(self._do_chat)(body)
        except services.PartyError as exc:
            await self.send_json({'type': 'error', 'message': exc.message})
            return
        await self.group_send_event({'type': 'chat', 'message': message})

    def _do_chat(self, body):
        from apps.users.profile import avatar_url
        party = services.get_open(self.code)
        msg = services.add_message(party, self.scope['user'], body)
        return {
            'id': msg.id,
            'user_id': msg.user_id,
            'username': self.scope['user'].username,
            'photo': avatar_url(self.scope['user']),
            'body': msg.body,
            'created_at': msg.created_at.isoformat(),
        }

    async def _control(self, mode):
        try:
            party = await database_sync_to_async(self._do_control)(mode)
        except services.PartyError as exc:
            await self.send_json({'type': 'error', 'message': exc.message})
            return
        await self.group_send_event({
            'type': 'state',
            'party': await database_sync_to_async(services.party_payload)(party),
            'by': self.user_id,
        })

    def _do_control(self, mode):
        party = services.get_open(self.code)
        return services.set_control(party, self.scope['user'], mode)

    async def _signal(self, content):
        target = content.get('to')
        if target is None:
            return
        await self.channel_layer.group_send(
            f'party_{self.code}_u_{int(target)}',
            {
                'type': 'party.event',
                'payload': {
                    'type': 'signal',
                    'from': self.user_id,
                    'to': int(target),
                    'data': content.get('data') or {},
                },
            },
        )

    async def _camera(self, on, mic=None):
        await database_sync_to_async(presence.set_media)(
            self.code, self.user_id, camera=on, mic=mic,
        )
        await self.group_send_event({
            'type': 'camera',
            'user_id': self.user_id,
            'on': on,
            'mic': mic,
            'members': await database_sync_to_async(presence.members)(self.code),
        })
