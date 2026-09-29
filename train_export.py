"""
QRGuard - train the decision tree and export it as JavaScript.

Run this once:      python train_export.py
It prints the accuracy and writes tree.js, which we paste into index.html.

What this file does, in order:
  1. Load 10,000 phishing links and 20,000 normal links.
  2. Turn every link into the same 8 numbers that index.html counts.
  3. Train a decision tree on 24,000 links and score it on 6,000 unseen links.
  4. Print the trained tree as JavaScript if/else lines -> tree.js
  5. Check a few links, so we can compare Python and JavaScript by hand.

Needs: pandas, scikit-learn   (pip install pandas scikit-learn)
The three data files are not in this folder. See README.md for where to get them.
"""

import random

import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score

random.seed(0)          # same result every run


# ----------------------------------------------------------------------
# 1. The data
# ----------------------------------------------------------------------

# Phishing links reported by the public PhishTank database.
bad = list(pd.read_csv("data/phishing_urls.csv")["url"])[:10000]

# Normal links, part 1: the 10,000 most visited websites.
# We add a realistic page path to each one. Without this, every normal link
# would be a bare domain and the tree would learn "has a page path = phishing".
top = pd.read_csv("data/top10k_domains.txt", header=None)
pages = ["", "/login", "/account/login", "/pay", "/search?q=hi", "/news", "/menu", "/about"]

# 1 of these 10 starts with http, so about 10% of our normal links are not https.
# Without this the tree would learn "http = phishing", which is not true.
starts = ["https://www.", "https://", "https://www.", "https://", "http://www.",
          "https://", "https://www.", "https://", "https://", "https://"]

good = []
for site in top[0]:
    good.append(random.choice(starts) + site + random.choice(pages))

# Normal links, part 2: 10,000 real links from a public list of safe URLs.
real = list(pd.read_csv("data/benign_urls.csv", header=None, names=["url"])["url"].dropna())
random.shuffle(real)
good = good + real[:10000]


# ----------------------------------------------------------------------
# 2. The 8 features
#    index.html counts exactly the same 8 things, in the same order.
# ----------------------------------------------------------------------

words = ["login", "verify", "account", "update", "secure", "bank", "pay", "signin", "confirm"]
bad_endings = [".xyz", ".top", ".tk", ".club", ".online", ".site", ".icu", ".work", ".gq", ".cf"]
NAMES = ["ip", "at", "dash", "words", "no_https", "length", "dots", "bad_ending"]


def get_features(link):
    """Turn one link into a list of 8 numbers."""
    link = link.lower()

    # the site name is everything before the first "/"
    site = link.replace("https://", "")
    site = site.replace("http://", "")
    site = site.split("/")[0]
    if "@" in site:
        site = site.split("@")[1]      # if there is an "@", the real site is after it

    # 1. is the site a number address like 192.0.2.44 ?
    ip = 0
    if site.replace(".", "").isdigit():
        ip = 1

    # 2. is there an "@" anywhere? It can hide the real site.
    at = 0
    if "@" in link:
        at = 1

    # 3. how many hyphens are in the site name?
    dash = site.count("-")

    # 4. how many scam words are in the link?
    count = 0
    for w in words:
        if w in link:
            count = count + 1

    # 5. is https missing?
    no_https = 0
    if not link.startswith("https"):
        no_https = 1

    # 6. how long is the site name?
    length = len(site)

    # 7. how many dots are in the site name?
    dots = site.count(".")

    # 8. does the site end with something scammers often use?
    bad_ending = 0
    for e in bad_endings:
        if site.endswith(e):
            bad_ending = 1

    return [ip, at, dash, count, no_https, length, dots, bad_ending]


X = []
y = []
for link in good:
    X.append(get_features(link))
    y.append(0)                    # 0 = safe
for link in bad:
    X.append(get_features(link))
    y.append(1)                    # 1 = phishing


# ----------------------------------------------------------------------
# 3. Train and score
# ----------------------------------------------------------------------

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)

# max_depth=5 keeps the tree small enough to draw and explain.
model = DecisionTreeClassifier(max_depth=5, random_state=0)
model.fit(X_train, y_train)

acc = model.score(X_test, y_test)
pred = model.predict(X_test)
print("accuracy:", round(acc * 100, 1), "%",
      " precision:", round(precision_score(y_test, pred) * 100, 1), "%",
      "  train", len(X_train), "/ test", len(X_test))


# ----------------------------------------------------------------------
# 4. Print the tree as JavaScript
#    Every node becomes an if/else. Every leaf becomes a return.
#    The output goes into index.html, so the browser needs no server.
# ----------------------------------------------------------------------

t = model.tree_


def emit(node, indent):
    pad = "  " * indent

    if t.children_left[node] == -1:            # a leaf
        safe, phish = t.value[node][0]
        p = phish / (safe + phish)             # how many links here were phishing
        return pad + "return " + str(round(p, 2)) + ";\n"

    name = NAMES[t.feature[node]]
    thr = t.threshold[node]
    s = pad + "if (f." + name + " <= " + str(round(thr, 1)) + ") {\n"
    s += emit(t.children_left[node], indent + 1)
    s += pad + "} else {\n"
    s += emit(t.children_right[node], indent + 1)
    s += pad + "}\n"
    return s


js = "// GENERATED by train_export.py - do not edit by hand.\n"
js += "// Decision tree trained on 24,000 links. Accuracy " + str(round(acc * 100, 1)) + "%\n"
js += "function phishingRisk(f) {\n" + emit(0, 1) + "}\n"
open("tree.js", "w", encoding="utf-8").write(js)
print("wrote tree.js -", len(js.splitlines()), "lines")


# ----------------------------------------------------------------------
# 5. Check a few links
#    We run the same links in the browser and compare the numbers, so we
#    know the JavaScript really does the same thing as Python.
# ----------------------------------------------------------------------

checks = [
    ("https://www.naver.com", "safe"),
    ("https://en.wikipedia.org/wiki/QR_code", "safe"),
    ("https://accounts.google.com/signin", "safe"),
    ("http://192.0.2.44/paypal/login.php", "phishing"),
    ("http://paypal-secure-login.account-verify.example/signin", "phishing"),
    ("https://free-gift-event.xyz/login", "phishing"),
]

for link, should_be in checks:
    p = model.predict_proba([get_features(link)])[0][1]
    guess = "phishing" if p >= 0.4 else "safe"
    print("OK " if guess == should_be else "BAD", round(float(p), 2), link)
