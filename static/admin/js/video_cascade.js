document.addEventListener("DOMContentLoaded", function () {
    const episodeSelect = document.getElementById("id_episode");
    if (!episodeSelect) return;

    // --- Season select yaratish ---
    const seasonSelect = document.createElement("select");
    seasonSelect.innerHTML = '<option value="">--- Season tanlang ---</option>';
    seasonSelect.style.cssText = "margin-left:10px; min-width:200px;";

    const seasonLabel = document.createElement("label");
    seasonLabel.textContent = "Season:";
    seasonLabel.style.fontWeight = "bold";

    const seasonDiv = document.createElement("div");
    seasonDiv.className = "form-row";
    seasonDiv.style.padding = "8px 0";
    seasonDiv.appendChild(seasonLabel);
    seasonDiv.appendChild(seasonSelect);

    // --- Anime select yaratish ---
    const animeSelect = document.createElement("select");
    animeSelect.innerHTML = '<option value="">--- Yuklanmoqda... ---</option>';
    animeSelect.style.cssText = "margin-left:10px; min-width:200px;";

    const animeLabel = document.createElement("label");
    animeLabel.textContent = "Anime:";
    animeLabel.style.fontWeight = "bold";

    const animeDiv = document.createElement("div");
    animeDiv.className = "form-row";
    animeDiv.style.padding = "8px 0";
    animeDiv.appendChild(animeLabel);
    animeDiv.appendChild(animeSelect);

    // Episode select oldiga season va anime'ni qo'shamiz
    const episodeRow = episodeSelect.closest(".form-row");
    episodeRow.insertAdjacentElement("beforebegin", seasonDiv);
    seasonDiv.insertAdjacentElement("beforebegin", animeDiv);

    function resetSeasons() {
        seasonSelect.innerHTML = '<option value="">--- Season tanlang ---</option>';
    }
    function resetEpisodes() {
        episodeSelect.innerHTML = '<option value="">--- Episode tanlang ---</option>';
    }

    // --- Animalarni yuklash ---
    fetch("/admin/episode/video/get-animes/")
        .then(r => r.json())
        .then(animes => {
            animeSelect.innerHTML = '<option value="">--- Anime tanlang ---</option>';
            animes.forEach(a => {
                const opt = document.createElement("option");
                opt.value = a.id;
                opt.textContent = a.title;
                animeSelect.appendChild(opt);
            });
        })
        .catch(() => {
            animeSelect.innerHTML = '<option value="">Xatolik yuz berdi</option>';
        });

    // --- Anime o'zgarganda seasonlarni yuklash ---
    animeSelect.addEventListener("change", function () {
        resetSeasons();
        resetEpisodes();
        const animeId = this.value;
        if (!animeId) return;

        fetch(`/admin/episode/video/seasons-by-anime/${animeId}/`)
            .then(r => r.json())
            .then(seasons => {
                seasons.forEach(s => {
                    const opt = document.createElement("option");
                    opt.value = s.id;
                    opt.textContent = `Season ${s.number}`;
                    seasonSelect.appendChild(opt);
                });
            });
    });

    // --- Season o'zgarganda episodelarni yuklash ---
    seasonSelect.addEventListener("change", function () {
        resetEpisodes();
        const seasonId = this.value;
        if (!seasonId) return;

        fetch(`/admin/episode/video/episodes-by-season/${seasonId}/`)
            .then(r => r.json())
            .then(episodes => {
                episodes.forEach(e => {
                    const opt = document.createElement("option");
                    opt.value = e.id;
                    opt.textContent = `E${e.number} - ${e.title}`;
                    episodeSelect.appendChild(opt);
                });
            });
    });
});