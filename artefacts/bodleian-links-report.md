# Bodleian links — dry-run match report (issue #64)

- Bodleian clone indexed: **11122** TEI files, **11124** shelfmark idnos.
- DIMEV Bodleian Library entries: **609** (598 type=manuscript [linked], 11 type=printed [excluded — see footprint]).
- Matched: **506** (293 exact, 213 after abbreviation folding).
- Ambiguous (normalized to >1 Bodleian record): **2**.
- Near miss (close Bodleian record exists — likely a shelfmark discrepancy to reconcile): **14**.
- Absent (no close record in medieval-mss — uncatalogued there, lost, or DIMEV-only): **76**.
- Of matched, **209** have at least one digital facsimile.
- Already carry links in DIMEV (skip on write): 0 catalogue, 10 surrogates.

## Printed-book footprint (type="printed", excluded from linking)

11 Bodleian entries are copies of printed books. The Bodleian catalogue records manuscripts only, so these are not linked. Any apparent hit below is a shelfmark-string collision with an unrelated manuscript, not a real match.

- Would-be exact/abbrev hits (spurious): **1**
- Would-be ambiguous: **0**
- Would-be near miss: **1**
- No Bodleian record at all: **9**

Spurious would-be matches (excluded because type=printed):

| DIMEV xml:id | DIMEV idno | Collided with |
|---|---|---|
| Bod88 | Bodley 88 | MS. Bodl. 88* |

## Matched only after abbreviation folding

DIMEV's spelling differs from the Bodleian's by convention only. Consider regularizing the DIMEV shelfmark.

| DIMEV xml:id | DIMEV idno | Bodleian shelfmark |
|---|---|---|
| BodAddA106 | Addit. A.106 | MS. Add. A. 106 |
| BodAddA11 | Addit. A.11 | MS. Add. A. 11 |
| BodAddA268 | Addit. A.268 | MS. Add. A. 268 |
| BodAddA369 | Addit. A.369 | MS. Add. A. 369 |
| BodAddB107 | Addit. B.107 | MS. Add. B. 107 |
| BodAddB60 | Addit. B.60 | MS. Add. B. 60 |
| BodAddB66 | Addit. B.66 | MS. Add. B. 66 |
| BodAddC220 | Addit. C.220 | MS. Add. C. 220 |
| BodAddC280 | Addit. C.280 | MS. Add. C. 280 |
| BodAddC38 | Addit. C.38 | MS. Add. C. 38 |
| BodAddE4 | Addit. E.4 | MS. Add. E. 4 (R) |
| BodAddE6 | Addit. E.6 | MS. Add. E. 6 (R) |
| BodAddE7 | Addit. E.7 | MS. Add. E. 7 (R) |
| BodAshRol21 | Ashmole Rolls 21 | MS. Ash. Rolls 21 |
| BodAshRol40 | Ashmole Rolls 40 | MS. Ash. Rolls 40 |
| BodAshRol52 | Ashmole Rolls 52 | MS. Ash. Rolls 52 |
| BodLatLitE10 | Bodl. Lat. liturg. e.10 | MS. Lat. liturg. e. 10 |
| BodLatLitE17 | Bodl. Lat. liturg. e.17 | MS. Lat. liturg. e. 17 |
| BodLatLitE47 | Bodl. Lat. liturg. e.47 | MS. Lat. liturg. e. 47 |
| BodLatLitG1 | Bodl. Lat. liturg. g.1 | MS. Lat. liturg. g. 1 |
| BodLatLitG8 | Bodl. Lat. liturg. g.8 | MS. Lat. liturg. g. 8 |
| Bod100 | Bodley 100 | MS. Bodl. 100 |
| Bod110 | Bodley 110 | MS. Bodl. 110 |
| Bod120 | Bodley 120 | MS. Bodl. 120 |
| Bod123 | Bodley 123 | MS. Bodl. 123 |
| Bod131 | Bodley 131 | MS. Bodl. 131 |
| Bod187 | Bodley 187 | MS. Bodl. 187 |
| Bod220 | Bodley 220 | MS. Bodl. 220 |
| Bod221 | Bodley 221 | MS. Bodl. 221 |
| Bod231 | Bodley 231 | MS. Bodl. 231 |
| Bod26 | Bodley 26 | MS. Bodl. 26 |
| Bod263 | Bodley 263 | MS. Bodl. 263 |
| Bod264 | Bodley 264 | MS. Bodl. 264 |
| Bod283 | Bodley 283 | MS. Bodl. 283 |
| Bod294 | Bodley 294 | MS. Bodl. 294 |
| Bod315 | Bodley 315 | MS. Bodl. 315 |
| Bod332 | Bodley 332 | MS. Bodl. 332 |
| Bod34 | Bodley 34 | MS. Bodl. 34 |
| Bod343 | Bodley 343 | MS. Bodl. 343 |
| Bod393 | Bodley 393 | MS. Bodl. 393 |
| Bod410 | Bodley 410 | MS. Bodl. 410 |
| Bod414 | Bodley 414 | MS. Bodl. 414 |
| Bod415 | Bodley 415 | MS. Bodl. 415 |
| Bod416 | Bodley 416 | MS. Bodl. 416 |
| Bod42 | Bodley 42 | MS. Bodl. 42 |
| Bod423 | Bodley 423 | MS. Bodl. 423 |
| Bod424 | Bodley 424 | MS. Bodl. 424 |
| Bod425 | Bodley 425 | MS. Bodl. 425 |
| Bod435 | Bodley 435 | MS. Bodl. 435 |
| Bod446 | Bodley 446 | MS. Bodl. 446 |
| Bod457 | Bodley 457 | MS. Bodl. 457 |
| Bod48 | Bodley 48 | MS. Bodl. 48 |
| Bod480 | Bodley 480 | MS. Bodl. 480 |
| Bod483 | Bodley 483 | MS. Bodl. 483 |
| Bod505 | Bodley 505 | MS. Bodl. 505 |
| Bod534 | Bodley 534 | MS. Bodl. 534 |
| Bod54 | Bodley 54 | MS. Bodl. 54 |
| Bod546 | Bodley 546 | MS. Bodl. 546 |
| Bod549 | Bodley 549 | MS. Bodl. 549 |
| Bod565 | Bodley 565 | MS. Bodl. 565 |
| Bod57 | Bodley 57 | MS. Bodl. 57 |
| Bod596 | Bodley 596 | MS. Bodl. 596 |
| Bod608 | Bodley 608 | MS. Bodl. 608 |
| Bod61 | Bodley 61 | MS. Bodl. 61 |
| Bod622 | Bodley 622 | MS. Bodl. 622 |
| Bod623 | Bodley 623 | MS. Bodl. 623 |
| Bod638 | Bodley 638 | MS. Bodl. 638 |
| Bod648 | Bodley 648 | MS. Bodl. 648 |
| Bod649 | Bodley 649 | MS. Bodl. 649 |
| Bod652 | Bodley 652 | MS. Bodl. 652 |
| Bod678 | Bodley 678 | MS. Bodl. 678 |
| Bod686 | Bodley 686 | MS. Bodl. 686 |
| Bod687 | Bodley 687 | MS. Bodl. 687 |
| Bod692 | Bodley 692 | MS. Bodl. 692 |
| Bod693 | Bodley 693 | MS. Bodl. 693 |
| Bod75 | Bodley 75 | MS. Bodl. 75 |
| Bod754 | Bodley 754 | MS. Bodl. 754 |
| Bod758 | Bodley 758 | MS. Bodl. 758 |
| Bod77 | Bodley 77 | MS. Bodl. 77 |
| Bod770 | Bodley 770 | MS. Bodl. 770 |
| Bod776 | Bodley 776 | MS. Bodl. 776 |
| Bod779 | Bodley 779 | MS. Bodl. 779 |
| Bod789 | Bodley 789 | MS. Bodl. 789 |
| Bod791 | Bodley 791 | MS. Bodl. 791 |
| Bod797 | Bodley 797 | MS. Bodl. 797 |
| Bod814 | Bodley 814 | MS. Bodl. 814 |
| Bod828 | Bodley 828 | MS. Bodl. 828 |
| Bod832 | Bodley 832 | MS. Bodl. 832 |
| Bod840 | Bodley 840 | MS. Bodl. 840 |
| Bod841 | Bodley 841 | MS. Bodl. 841 |
| Bod85 | Bodley 85 | MS. Bodl. 85 |
| Bod850 | Bodley 850 | MS. Bodl. 850 |
| Bod851 | Bodley 851 | MS. Bodl. 851 |
| Bod857 | Bodley 857 | MS. Bodl. 857 |
| Bod859 | Bodley 859 | MS. Bodl. 859 |
| Bod89 | Bodley 89 | MS. Bodl. 89 |
| Bod9 | Bodley 9 | MS. Bodl. 9 |
| Bod902 | Bodley 902 | MS. Bodl. 902 |
| Bod912 | Bodley 912 | MS. Bodl. 912 |
| Bod921 | Bodley 921 | MS. Bodl. 921 |
| Bod939 | Bodley 939 | MS. Bodl. 939 |
| Bod99 | Bodley 99 | MS. Bodl. 99 |
| BodRo1 | Bodley Rolls 1 | MS. Bodl. Rolls 1 |
| BodRo16 | Bodley Rolls 16 | MS. Bodl. Rolls 16 |
| BodRo22 | Bodley Rolls 22 | MS. Bodl. Rolls 22 |
| BodEngTheold36 | Eng. theol. d. 36 | MS. Eng. th. d. 36 |
| BodEngTheole1 | Eng. theol. e.1 | MS. Eng. th. e. 1 |
| BodEngTheole16 | Eng. theol. e.16 | MS. Eng. th. e. 16 |
| BodEngTheole181 | Eng. theol. e.181 | MS. Eng. th. e. 181 |
| BodEngTheolf39 | Eng. theol. f.39 | MS. Eng. th. f. 39 |
| BodHatDon1 | Hatton Donati 1 | MS. Hatton donat. 1 |
| BodLatTheD1 | Lat. theol. d.1 | MS. Lat. th. d. 1 |
| BodLatTheD15 | Lat. theol. d.15 | MS. Lat. th. d. 15 |
| BodRawA273 | Rawlinson A.273 | MS. Rawl. A. 273 |
| BodRawA338 | Rawlinson A.338 | MS. Rawl. A. 338 |
| BodRawA362 | Rawlinson A.362 | MS. Rawl. A. 362 |
| BodRawA366 | Rawlinson A.366 | MS. Rawl. A. 366 |
| BodRawA389 | Rawlinson A.389 | MS. Rawl. A. 389 |
| BodRawB166 | Rawlinson B.166 | MS. Rawl. B. 166 |
| BodRawB171 | Rawlinson B.171 | MS. Rawl. B. 171 |
| BodRawB187 | Rawlinson B.187 | MS. Rawl. B. 187 |
| BodRawB190 | Rawlinson B.190 | MS. Rawl. B. 190 |
| BodRawB196 | Rawlinson B.196 | MS. Rawl. B. 196 |
| BodRawB205 | Rawlinson B.205 | MS. Rawl. B. 205 |
| BodRawB214 | Rawlinson B.214 | MS. Rawl. B. 214 |
| BodRawB216 | Rawlinson B.216 | MS. Rawl. B. 216 |
| BodRawB306 | Rawlinson B.306 | MS. Rawl. B. 306 |
| BodRawB332 | Rawlinson B.332 | MS. Rawl. B. 332 |
| BodRawB408 | Rawlinson B.408 | MS. Rawl. B. 408 |
| BodRawC22 | Rawlinson C.22 | MS. Rawl. C. 22 |
| BodRawC285 | Rawlinson C.285 | MS. Rawl. C. 285 |
| BodRawC288 | Rawlinson C.288 | MS. Rawl. C. 288 |
| BodRawC301 | Rawlinson C.301 | MS. Rawl. C. 301 |
| BodRawC307 | Rawlinson C.307 | MS. Rawl. C. 307 |
| BodRawC316 | Rawlinson C.316 | MS. Rawl. C. 316 |
| BodRawC317 | Rawlinson C.317 | MS. Rawl. C. 317 |
| BodRawC319 | Rawlinson C.319 | MS. Rawl. C. 319 |
| BodRawC35 | Rawlinson C.35 | MS. Rawl. C. 35 |
| BodRawC401 | Rawlinson C.401 | MS. Rawl. C. 401 |
| BodRawC446 | Rawlinson C.446 | MS. Rawl. C. 446 |
| BodRawC448 | Rawlinson C.448 | MS. Rawl. C. 448 |
| BodRawC48 | Rawlinson C.48 | MS. Rawl. C. 48 |
| BodRawC506 | Rawlinson C.506 | MS. Rawl. C. 506 |
| BodRawC510 | Rawlinson C.510 | MS. Rawl. C. 510 |
| BodRawC534 | Rawlinson C.534 | MS. Rawl. C. 534 |
| BodRawC572 | Rawlinson C.572 | MS. Rawl. C. 572 |
| BodRawC641 | Rawlinson C.641 | MS. Rawl. C. 641 |
| BodRawC655 | Rawlinson C.655 | MS. Rawl. C. 655 |
| BodRawC662 | Rawlinson C.662 | MS. Rawl. C. 662 |
| BodRawC670 | Rawlinson C.670 | MS. Rawl. C. 670 |
| BodRawC699 | Rawlinson C.699 | MS. Rawl. C. 699 |
| BodRawC72 | Rawlinson C.72 | MS. Rawl. C. 72 |
| BodRawC81 | Rawlinson C.81 | MS. Rawl. C. 81 |
| BodRawC813 | Rawlinson C.813 | MS. Rawl. C. 813 |
| BodRawC83 | Rawlinson C.83 | MS. Rawl. C. 83 |
| BodRawC86 | Rawlinson C.86 | MS. Rawl. C. 86 |
| BodRawC884 | Rawlinson C.884 | MS. Rawl. C. 884 |
| BodRawC890 | Rawlinson C.890 | MS. Rawl. C. 890 |
| BodRawC891 | Rawlinson C.891 | MS. Rawl. C. 891 |
| BodRawD251 | Rawlinson D.251 | MS. Rawl. D. 251 |
| BodRawD328 | Rawlinson D.328 | MS. Rawl. D. 328 |
| BodRawD82 | Rawlinson D.82 | MS. Rawl. D. 82 |
| BodRawD893 | Rawlinson D.893 | MS. Rawl. D. 893 |
| BodRawD913 | Rawlinson D.913 | MS. Rawl. D. 913 |
| BodRawD939 | Rawlinson D.939 | MS. Rawl. D. 939 |
| BodRawG18 | Rawlinson G.18 | MS. Rawl. G. 18 |
| BodRawG22 | Rawlinson G.22 | MS. Rawl. G. 22 |
| BodRawG59 | Rawlinson G.59 | MS. Rawl. G. 59 |
| BodRawQb4 | Rawlinson Q.b.4 | MS. Rawl. Q. b. 4 |
| BodRawlitd5 | Rawlinson liturg. d.5 | MS. Rawl. liturg. d. 5 |
| BodRawlite3 | Rawlinson liturg. e.3 | MS. Rawl. liturg. e. 3 |
| BodRawlite41 | Rawlinson liturg. e.41 | MS. Rawl. liturg. e. 41 |
| BodRawlite44 | Rawlinson liturg. e.44 | MS. Rawl. liturg. e. 44 |
| BodRawlite7 | Rawlinson liturg. e.7 | MS. Rawl. liturg. e. 7 |
| BodRawlitf36 | Rawlinson liturg. f.36 | MS. Rawl. liturg. f. 36 |
| BodRawlitg2 | Rawlinson liturg. g.2 | MS. Rawl. liturg. g. 2 |
| BodRawPoe10 | Rawlinson poet. 10 | MS. Rawl. poet. 10 |
| BodRawPoe118 | Rawlinson poet. 118 | MS. Rawl. poet. 118 |
| BodRawPoe137 | Rawlinson poet. 137 | MS. Rawl. poet. 137 |
| BodRawPoe138 | Rawlinson poet. 138 | MS. Rawl. poet. 138 |
| BodRawPoe139 | Rawlinson poet. 139 | MS. Rawl. poet. 139 |
| BodRawPoe14 | Rawlinson poet. 14 | MS. Rawl. poet. 14 |
| BodRawPoe140 | Rawlinson poet. 140 | MS. Rawl. poet. 140 |
| BodRawPoe141 | Rawlinson poet. 141 | MS. Rawl. poet. 141 |
| BodRawPoe143 | Rawlinson poet. 143 | MS. Rawl. poet. 143 |
| BodRawPoe144 | Rawlinson poet. 144 | MS. Rawl. poet. 144 |
| BodRawF145 | Rawlinson poet. 145 | MS. Rawl. poet. 145 |
| BodRawPoe149 | Rawlinson poet. 149 | MS. Rawl. poet. 149 |
| BodRawPoe151 | Rawlinson poet. 151 | MS. Rawl. poet. 151 |
| BodRawPoe163 | Rawlinson poet. 163 | MS. Rawl. poet. 163 |
| BodRawPoe168 | Rawlinson poet. 168 | MS. Rawl. poet. 168 |
| BodRawPoe175 | Rawlinson poet. 175 | MS. Rawl. poet. 175 |
| BodRawPoe223 | Rawlinson poet. 223 | MS. Rawl. poet. 223 |
| BodRawPoe225 | Rawlinson poet. 225 | MS. Rawl. poet. 225 |
| BodRawPoe241 | Rawlinson poet. 241 | MS. Rawl. poet. 241 |
| BodRawPoe32 | Rawlinson poet. 32 | MS. Rawl. poet. 32 |
| BodRawPoe34 | Rawlinson poet. 34 | MS. Rawl. poet. 34 |
| BodRawPoe35 | Rawlinson poet. 35 | MS. Rawl. poet. 35 |
| BodRawPoe36 | Rawlinson poet. 36 | MS. Rawl. poet. 36 |
| BodRawPoe38 | Rawlinson poet. 38 | MS. Rawl. poet. 38 |
| BodeMus1 | e Musaeo 1 | MS. e Mus. 1 |
| BodeMus124 | e Musaeo 124 | MS. e Mus. 124 |
| BodeMus160 | e Musaeo 160 | MS. e Mus. 160 |
| BodeMus181 | e Musaeo 181 | MS. e Mus. 181 |
| BodeMus23 | e Musaeo 23 | MS. e Mus. 23 |
| BodeMus232 | e Musaeo 232 | MS. e Mus. 232 |
| BodeMus35 | e Musaeo 35 | MS. e Mus. 35 |
| BodeMus52 | e Musaeo 52 | MS. e Mus. 52 |
| BodeMus53 | e Musaeo 53 | MS. e Mus. 53 |
| BodeMus63 | e Musaeo 63 | MS. e Mus. 63 |
| BodeMus76 | e Musaeo 76 | MS. e Mus. 76 |
| BodeMus86 | e Musaeo 86 | MS. e Mus. 86 |
| BodeMus88 | e Musaeo 88 | MS. e Mus. 88 |

## Ambiguous — normalized to more than one Bodleian record

| DIMEV xml:id | DIMEV idno | Bodleian shelfmarks |
|---|---|---|
| BodSelSup102 | Selden Supra 102 | MS. Selden Supra 102*; MS. Selden Supra 102 |
| BodeMus198 | e Musaeo 198 | MS. e Mus. 198*; MS. e Mus. 198 |

## Near miss — probable shelfmark discrepancy to reconcile

A close Bodleian record exists, so this is most likely a spelling difference rather than an absent manuscript. Verify before linking; fix the DIMEV shelfmark if it is wrong.

| DIMEV xml:id | DIMEV idno | Closest Bodleian shelfmark |
|---|---|---|
| BodArchDd1 | Arch. Dd.1 | MS. Bywater adds. 1 |
| BodAsh48 | Ashmole 48 | MS. Marshall 48 |
| BodAsh50 | Ashmole 50 | MS. Ash. Rolls 50 |
| BodAsh53 | Ashmole 53 | MS. Ash. Rolls 53 |
| BodDouAdd137 | Douce Addit. 137 | MS. Douce 137 |
| BodEngTheole15 | Eng. theol. e.15 | MS. Eng. poet. e. 15 |
| BodEngTheole17 | Eng. theol. e.17 | MS. Eng. poet. e. 17 |
| BodEngTheole18 | Eng. theol. e.18 | MS. Lat. th. e. 18 |
| BodEngTheole94 | Eng. theol. e.94 | MS. Eng. poet. e. 94 |
| BodJam34 | James 34 | MS. Ashmole 34 |
| BodJam6 | James 6 | MS. Ashmole 6 |
| BodMal4 | Malone 4 | MS. Hamilton 4 |
| BodRawPoe13 | Rawlinson poet. 13 | MS. Roe 13 |
| BodTan88 | Tanner 88 | MS. Canon. Gr. 88 |

## Absent — no close record in medieval-mss

Nothing comparable in the clone. The Bodleian's coverage is partial (e.g. only some Ashmole MSS), so most of these are simply not catalogued there; some may be lost, composite, or DIMEV-only. No link to supply; no action unless the shelfmark itself looks wrong.

| DIMEV xml:id | DIMEV idno |
|---|---|
| Bod80G40Med | 80.G.40.Med |
| BodAddA60 | Addit. A.60 |
| BodAddC287 | Addit. C.287 |
| BodArchGe35 | Arch. G.e 35 |
| BodArcSelC813 | Arch. Selden C. 813 |
| BodAsh1382 | Ashmole 1382, Part II |
| BodAsh1386 | Ashmole 1386 |
| BodAsh1394XIiii | Ashmole 1394, Part XI.iii |
| BodAsh1418 | Ashmole 1418 |
| BodAsh1442 | Ashmole 1442, Part VI |
| BodAsh1445 | Ashmole 1445 |
| BodAsh1449 | Ashmole 1449 |
| BodAsh1464 | Ashmole 1464 |
| BodAsh1487 | Ashmole 1487, Part II |
| BodAsh1490 | Ashmole 1490 |
| BodAsh1491 | Ashmole 1491 |
| BodAsh176 | Ashmole 176 |
| BodAsh1835 | Ashmole 1835 |
| BodAsh241 | Ashmole 241 |
| BodAsh57 | Ashmole 57 |
| BodAsh781 | Ashmole 781 |
| BodAsh863 | Ashmole 863 |
| Bod175 | Bodley 175 |
| Bod2C | Bodley 2C dep. C12930 |
| BodCorne2 | Corn e.2 |
| BodCorne3 | Corn. e.3 |
| BodDepc130 | Dep. c.130 |
| BodDepd324 | Dep. d.324 |
| BodDod10 | Dodsworth 10 |
| BodDod116 | Dodsworth 116 |
| BodDod147 | Dodsworth 147 |
| BodDod160 | Dodsworth 160 |
| BodDod50 | Dodsworth 50 |
| BodDod55 | Dodsworth 55 |
| BodDod95 | Dodsworth 95 |
| BodDou124 | Douce 124 |
| BodDou170 | Douce 170 |
| BodDou175 | Douce 175 |
| BodDou261 | Douce 261 |
| BodDou309 | Douce 309 |
| BodDou376 | Douce 376 |
| BodDou65 | Douce 65 |
| BodEngmiscc95 | Eng. misc. c.95 |
| BodEngMise241 | Eng. misc. e.241 |
| BodEngPoetb5 | Eng. poet. b.5 |
| BodEngPoetd27 | Eng. poet. d.27 |
| BodEngPoetf1 | Eng. poet. f.1 |
| BodFacsd24 | Facs. d.24 |
| BodFacse23 | Facs. e.23 |
| BodFird14 | Firth d.14 |
| BodHerD104 | Hearne's Diary 104 |
| BodRawK38 | Hearne's diaries 38 |
| BodRawK42 | Hearne's diaries 42 |
| BodJones8 | Jones 8 |
| BodKentCh233 | Kent Charter 233 |
| BodLatMisB17 | Lat. misc. b.17, no. 152 |
| BodNorthC80 | North C.80 |
| BodRaw4 | Rawlinson 4to 598 (10) |
| BodRawB252 | Rawlinson B.252 |
| BodRawB471 | Rawlinson B.471 |
| BodRawC85 | Rawlinson C.85 |
| BodRawD1046 | Rawlinson D.1046 |
| BodRawD1062 | Rawlinson D.1062 |
| BodRawD375 | Rawlinson D.375 |
| BodRawPoe121 | Rawlinson poet. 121 |
| BodRawPoe172 | Rawlinson poet. 172 |
| BodRawPoe182 | Rawlinson poet. 182 |
| BodRawPoe26 | Rawlinson poet. 26 |
| BodTan383 | Tanner 383 |
| BodVetElc65 | Vet. El. c.65 |
| BodWoodB15 | Wood B.15 |
| BodWoodD18 | Wood D.18 |
| BodWoodE1 | Wood E.1 |
| BodeMus180 | e Musaeo 180 |
| BodeMus243 | e Musaeo 243 |
| BodeMus75 | e Musaeo 75 |
