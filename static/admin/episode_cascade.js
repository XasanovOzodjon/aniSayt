document.addEventListener("DOMContentLoaded", function () {
    const seasonSelect = document.getElementById("id_season");
    if (!seasonSelect) return;

    // --- Anime select yaratish ---
    const animeSelect = document.createElement("select");
    animeSelect.id = "anime_selector";
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

    seasonSelect.closest(".form-row").insertAdjacentElement("beforebegin", animeDiv);

    // Season select'ni reset qilish helper
    function resetSeason() {
        seasonSelect.innerHTML = '<option value="">--- Season tanlang ---</option>';
    }

    // --- Animalarni yuklash ---
    fetch("/admin/episode/episode/get-animes/")
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
        const animeId = this.value;
        resetSeason();
        if (!animeId) return;

        fetch(`/admin/episode/episode/seasons-by-anime/${animeId}/`)
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
});