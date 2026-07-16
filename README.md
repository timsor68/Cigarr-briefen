# Cigarr-briefen

Nyheter, test och fakta om cigarrer — på svenska och engelska.

## Innehåll

- `index.html` — förstasida
- `nyheter.html` — nyhetsflöde (platshållare)
- `test.html` — recensioner (platshållare)
- `fakta.html` — kunskapsbank om cigarrer
- `style.css` — gemensam styling
- `cigarr-briefen-plan.md` — strukturplan för projektet (innehållskällor, juridik, teknisk ansats)

## Köra lokalt

Öppna `index.html` direkt i webbläsaren, eller kör en enkel server:

```
python3 -m http.server 8000
```

och besök `http://localhost:8000`.

## Publicera med GitHub Pages

1. Skapa ett nytt repo på GitHub (t.ex. `cigarr-briefen`)
2. Pusha den här mappens innehåll dit
3. Gå till repots **Settings → Pages**, välj branch `main` och mappen `/ (root)`
4. Sajten blir tillgänglig på `https://<användarnamn>.github.io/cigarr-briefen/`
