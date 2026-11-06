const paths = {
  back: '<path d="m14 6-6 6 6 6"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/>',
  swap: '<path d="M4 8h16m-4-4 4 4-4 4M20 16H4m4-4-4 4 4 4"/>',
  arrow: '<path d="M5 12h14m-6-6 6 6-6 6"/>',
  fit: '<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/>',
  layers: '<path d="m12 3 10 6-10 6L2 9Zm-9 12 9 6 9-6M3 15l9 6 9-6"/>',
  orbit: '<ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(-35 12 12)"/><circle cx="12" cy="12" r="3"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 0 1 5 0c0 2-2.5 2-2.5 4m0 3v.1"/>',
  present: '<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M12 17v4m-4 0h8m-8-9 3-3 3 3 3-4"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  minus: '<path d="M5 12h14"/>',
  person: '<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
  route: '<circle cx="5" cy="5" r="2"/><circle cx="19" cy="19" r="2"/><path d="M7 5h8a4 4 0 0 1 0 8H9a4 4 0 0 0 0 8h8"/>',
  reset: '<path d="M3 10a9 9 0 1 1 2 8M3 4v6h6"/>',
  external: '<path d="M14 3h7v7m0-7L10 14M10 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5"/>',
  chevron: '<path d="m8 5 7 7-7 7"/>'
};

export const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || ""}</svg>`;
export const initials = name => name.trim().split(/\s+/).filter(Boolean).filter((part, index, parts) => index === 0 || index === parts.length - 1).map(part => part[0]).join("");
export const palette = ["#a9c7ff", "#d8b7ed", "#b6dcce", "#f0cbb0", "#b8c0ed", "#d6d8b2"];

export function atlasMarkup(gaps) {
  return `
    <div class="atlas-viewport"></div><div class="atlas-vignette" aria-hidden="true"></div>
    <div class="atlas-head" data-obstruct>
      <button class="atlas-back" type="button" data-action="exit">${icon("back")}<span>Drzewo 2D</span></button>
      <div class="atlas-brand">${icon("orbit")}<h2>Atlas rodzinny</h2><span>3D</span></div>
      <div class="atlas-head-actions"><button type="button" data-action="help" aria-controls="atlas-guide" aria-expanded="false" title="Jak korzystać z atlasu">${icon("help")}<span>Przewodnik</span></button><button type="button" data-action="present" aria-pressed="false" title="Tryb prezentacji (P)">${icon("present")}<span>Prezentuj</span></button></div>
    </div>
    <div class="atlas-overview" data-obstruct><h3>Historie<br>blisko siebie.</h3><p>Cała rodzina w jednej przestrzeni.<br>Obróć drzewo. Odkryj połączenia.</p><span class="atlas-scene-count"></span></div>
    <div class="atlas-context" data-obstruct><label class="atlas-scope-label">${icon("layers")}<select class="atlas-scope" aria-label="Zakres atlasu"><option value="all">Całe drzewo</option><option value="family" disabled>Otoczenie osoby</option><option value="route" disabled>Tylko połączenie</option></select></label><button type="button" data-action="overview" title="Wyczyść wybór i wróć do całego drzewa" hidden>${icon("reset")}<span>Całość</span></button></div>
    <div class="atlas-status" role="status" aria-live="polite" aria-atomic="true"></div>
    <section class="atlas-inspector atlas-glass" aria-label="Przebieg połączenia" data-obstruct hidden><div class="atlas-story"></div></section>
    <section class="atlas-selected atlas-glass" aria-label="Wybrana osoba" data-obstruct hidden></section>
    <section class="atlas-key atlas-glass" id="atlas-guide" aria-label="Przewodnik po atlasie" data-obstruct hidden>
      <div class="atlas-panel-head"><h3>Odkrywaj w swoim tempie</h3><button type="button" data-action="help" aria-label="Zamknij przewodnik">${icon("close")}</button></div>
      <dl class="atlas-instructions"><div><dt>Obrót</dt><dd>Przeciągnij jednym palcem lub myszą</dd></div><div><dt>Przybliżenie</dt><dd>Kółko myszy lub gest dwoma palcami</dd></div><div><dt>Przesuwanie</dt><dd>Prawy przycisk myszy lub przycisk „Przesuń”</dd></div><div><dt>Osoba</dt><dd>Kliknij imię lub punkt. Dwa kliknięcia przybliżają.</dd></div></dl>
      <div class="atlas-key-lines"><p><i class="atlas-key-line route"></i>Wybrane połączenie</p><p><i class="atlas-key-line"></i>Rodzic i dziecko</p><p><i class="atlas-key-line spouse"></i>Małżeństwo</p><p><i class="atlas-key-line hypothesis"></i>Hipotetyczna relacja</p></div>
      <p>Kolory rozróżniają gałęzie, nie pewność informacji. Wyżej są starsze pokolenia, nie dokładne lata. Powtórzenia przodków mogą łączyć różne warstwy.</p><p>„Akt”, „poszlaka” i „hipoteza” opisują wpis osoby, nie dowód całego połączenia. Wspólne dziecko nie oznacza małżeństwa. ${gaps} oznaczeń luk badawczych pozostaje w 2D.</p>
      <label class="atlas-hypothesis-option"><input class="atlas-hypotheses" type="checkbox"><span>Uwzględnij hipotetyczne relacje<small>Domyślnie atlas ich nie łączy.</small></span></label>
      <p class="atlas-shortcuts"><kbd>F</kbd> dopasuj <kbd>P</kbd> prezentacja <kbd>Esc</kbd> zamknij</p>
    </section>
    <div class="atlas-tools atlas-glass" role="group" aria-label="Sterowanie atlasem" data-obstruct>
      <button type="button" data-action="fit" aria-label="Dopasuj drzewo do ekranu" title="Dopasuj (F)">${icon("fit")}</button><button type="button" data-action="in" aria-label="Powiększ" title="Powiększ">${icon("plus")}</button><button type="button" data-action="out" aria-label="Pomniejsz" title="Pomniejsz">${icon("minus")}</button><span class="atlas-tool-divider"></span><button type="button" data-action="flat" aria-pressed="false" aria-label="Płaski widok" title="Płaski widok">${icon("layers")}</button><button type="button" data-action="touch" aria-pressed="false" aria-label="Przełącz przeciąganie na przesuwanie" title="Przełącz obrót / przesuwanie">${icon("orbit")}</button>
    </div>
    <div class="atlas-orientation" aria-hidden="true"><span>Starsze pokolenia</span><i></i><span>Młodsze pokolenia</span></div>
    <div class="atlas-dock atlas-glass" data-obstruct>
      <div class="atlas-dock-caption"><span>${icon("route")}<span>Co Was łączy?</span></span><span>Wybierz dowolne dwie osoby</span></div>
      <form class="atlas-search" aria-label="Znajdź połączenie między osobami">
        <div class="atlas-field"><label for="atlas-from">Pierwsza osoba</label><div class="atlas-input-wrap">${icon("search")}<input id="atlas-from" type="search" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="atlas-options-0" autocomplete="off" placeholder="Imię i nazwisko"></div><div id="atlas-options-0" class="atlas-options" role="listbox" aria-label="Wyniki: pierwsza osoba" hidden></div></div>
        <button type="button" class="atlas-swap" data-action="swap" title="Zamień osoby" aria-label="Zamień osoby">${icon("swap")}</button>
        <div class="atlas-field"><label for="atlas-to">Druga osoba</label><div class="atlas-input-wrap">${icon("search")}<input id="atlas-to" type="search" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="atlas-options-1" autocomplete="off" placeholder="Imię i nazwisko"></div><div id="atlas-options-1" class="atlas-options" role="listbox" aria-label="Wyniki: druga osoba" hidden></div></div>
        <button class="atlas-primary" type="submit"><span>Połącz</span>${icon("arrow")}</button>
      </form>
    </div>
    <div class="atlas-foot"><span>Przeciągnij, aby obrócić <i>·</i> Przybliż, aby zobaczyć imiona</span><span>Dane pozostają w tym pliku</span></div>
    <button class="atlas-end-presentation atlas-glass" type="button" data-action="present" hidden>${icon("close")} Zakończ prezentację</button>
    <div class="atlas-failure atlas-glass" role="alert" data-obstruct hidden><strong>Widok 3D jest niedostępny</strong><p></p><button type="button" data-action="retry">Spróbuj ponownie</button><button type="button" data-action="exit">Wróć do drzewa 2D</button></div>`;
}
