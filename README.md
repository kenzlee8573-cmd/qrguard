# QRGuard

Code Monster 2026 · AI / Machine Learning · Team of 2

A web page that checks whether a QR code's link looks dangerous **before you open it**,
and shows the reason. It runs inside the browser, so there is no server and it works offline.

Try it: https://kenzlee8573-cmd.github.io/qrguard/

## Files

| File | What it is | Who wrote it |
|---|---|---|
| `index.html` | The whole app — screen, 8 features, tree, verdict | us |
| `train_export.py` | Trains the tree and prints it out as JavaScript | us |
| `tree.js` | What `train_export.py` prints. We pasted it into `index.html` | generated |
| `jsQR.js` | Finds the QR pattern in a camera picture | **not us** |

`jsQR.js` is an open-source library: https://github.com/cozmo/jsQR (Apache 2.0).
We use it as it is and did not change it.

## How to run

**The app**

```
python -m http.server 8000
```
Open `http://localhost:8000`. The camera only works on https or localhost — that is a
browser rule, which is why we host it on GitHub Pages. Without a camera you can still
paste a link and press Check.

**Training**

```
pip install pandas scikit-learn
python train_export.py
```

It prints the accuracy and writes `tree.js`. Put these three files in a `data/` folder first:

| Save as | Get it from |
|---|---|
| `data/phishing_urls.csv` | PhishTank — https://phishtank.org/ |
| `data/benign_urls.csv` | https://github.com/ebubekirbbr/pdd/blob/master/input/Benign_list_big_final.csv |
| `data/top10k_domains.txt` | https://github.com/zer0h/top-1000000-domains |

## How it works

**1. A link becomes 8 numbers.** A computer cannot read a link, so we count eight things.
We picked these eight ourselves.

| # | What we count | `www.naver.com` | `paypal-secure-login.account-verify.xyz` |
|---|---|---|---|
| 1 | Number address instead of a name | 0 | 0 |
| 2 | Contains `@` | 0 | 0 |
| 3 | Hyphens in the site name | 0 | 3 |
| 4 | Scam words (login, verify, pay …) | 0 | 6 |
| 5 | No https | 0 | 1 |
| 6 | Length of the site name | 13 | 38 |
| 7 | Dots in the site name | 2 | 2 |
| 8 | Bad ending (.xyz, .top …) | 0 | 1 |

`get_features()` in Python and `getFeatures()` in JavaScript count the same eight things
in the same order.

**2. A decision tree scores it.** scikit-learn, `max_depth=5`, trained on 24,000 links and
tested on 6,000 it had never seen.

```
accuracy 82.2%    precision 84.1%
```

The first two questions:

```
             site name length <= 17.5 ?        24,000 links, 33% phishing
       yes /                        \ no
  length <= 13.5 ?                  length <= 21.5 ?
  /        \                        /        \
14%        30%                    55%        91%
```

We chose what to count. The model chose the numbers — we never picked 17.5 or 13.5.

**3. The tree becomes JavaScript.** A scikit-learn model cannot run in a browser and we did
not want a server, so `train_export.py` walks the finished tree and prints it as `if`/`else`
lines into `tree.js`:

```javascript
function phishingRisk(f) {
  if (f.length <= 17.5) {
    if (f.length <= 13.5) {
      if (f.words <= 2.5) {
        ...
        return 0.13;
```

That code sits inside `index.html`, so the page carries the model with it.

**4. The verdict.** `0.70` and above is DANGER, `0.40` and above is CAUTION, below that is
SAFE. We picked those two numbers. Shortened links (bit.ly, tinyurl) skip the tree and
always get CAUTION, because the address shows nothing to judge. Then every feature that
fired is turned into a sentence, so the user sees why.

## What went wrong first

Our first model scored 97.7%, but it called `https://www.naver.com` DANGER. The problem was
our data: every normal link we had collected was a bare domain, so the tree learned "has a
page path = phishing". After we fixed that it learned "http = phishing", because all our
normal links were https. We fixed both, and the accuracy dropped to 82.2%.

## What it cannot do

We only read the address. If a normal website is hacked, the address still looks normal and
we miss it. QRGuard is a first check, not a guarantee.
