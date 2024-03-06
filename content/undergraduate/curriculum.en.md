---
title: Curriculum
description: Boğaziçi University Computer Enginering Curriculum
metadata: none
toc: false
weight: 1
---

Computer engineering program consist of
{{< badge title="core" color="danger" >}},
{{< badge title="mathematics" color="info" >}},
{{< badge title="hardware" color="success" >}},
{{< badge title="engineering" color="danger" >}},

```mermaid "caption=asdsad"
%%{ init: { 'flowchart': { 'curve': 'linear' } } }%%
flowchart TD

classDef cmpebox fill:#ff5555,stroke:none,stroke-width:2px,color:#eee
classDef math fill:#f1fa8c,stroke:none,stroke-width:2px, color:#333
classDef science fill:#ffb86c,stroke:none,stroke-width:2px
classDef general fill:none,stroke:#000,stroke-width:2px
classDef elective fill:none,stroke:#000,stroke-width:2px,stroke-dasharray: 5 5
classDef hardware fill:#50fa7b,stroke:none,stroke-width:2px, color:#333
classDef engineering fill:#bd93f9,stroke:none,stroke-width:2px, color:#eee
classDef external fill:none,stroke:#000,stroke-width:2px,stroke-dasharray: 5 5

CHEM105 ~~~~ EE210 --> EE212
PHYS121 --> PHYS201 --> PHYS202
MATH101 --> MATH102 ~~~ MATH201 --> MATH202
CMPE343 --> IE306
MATH201 ---> IE310
CMPE250 ~~~ CMPE260
MATH101 ~~~ HSS1 ~~~~~~~~ HSS2

MATH101 -----> CMPE343
MATH202 ---> CMPE362
CMPE160 ~~~ CMPE220 ----> CMPE350
CMPE250 --> CMPE260
CMPE250 ---> CMPE300 & CMPE322
CMPE250 ----> CMPE321
CMPE240 --> CMPE344
CMPE220 ~~~ CMPE240 ----> CMPE443
CMPE150 --> CMPE160 --> CMPE250
CMPE160 ---> CMPE230
CMPE352 & CMPE321 --> CMPE451
CMPE451 ~~~ CMPE492
CMPE350 ~~~ CC1 & CC2 & CC3
CMPE443 ~~~ CC4 & CC5 & CC6

EC101 --> EC102 ~~~ TK221 ~~~ TK222 ~~~ HTR311 ~~~ HTR312

MATH101("MATH101"):::math
MATH102("MATH102"):::math
MATH201("MATH201"):::math
MATH202("MATH202"):::math

CHEM105("CHEM105"):::science
PHYS121("PHYS121"):::science
PHYS201("PHYS201"):::science
PHYS202("PHYS202"):::science


HSS1("HSS"):::elective
HSS2("HSS"):::elective

IE306("IE306"):::engineering
IE310("IE310"):::engineering

EE210("EE210"):::engineering
EE212("EE212"):::engineering

EC101("EC101"):::general
EC102("EC102"):::general

CMPE150("CMPE150"):::cmpebox
CMPE160("CMPE160"):::cmpebox

CMPE220("CMPE220"):::math
CMPE230("CMPE230"):::cmpebox
CMPE240("CMPE240"):::hardware
CMPE250("CMPE250"):::cmpebox
CMPE260("CMPE260"):::cmpebox

CMPE300("CMPE300"):::cmpebox
CMPE321("CMPE321"):::cmpebox
CMPE322("CMPE322"):::cmpebox
CMPE343("CMPE343"):::math
CMPE344("CMPE344"):::hardware
CMPE350("CMPE350"):::cmpebox
CMPE352("CMPE352"):::engineering
CMPE362("CMPE362"):::engineering

CMPE443("CMPE443"):::hardware
CMPE451("CMPE451"):::cmpebox
CMPE492("CMPE492"):::cmpebox

TK221("TK221"):::general
TK222("TK222"):::general

HTR311("HTR311"):::general
HTR312("HTR312"):::general

CC1("CC"):::elective
CC2("CC"):::elective
CC3("CC"):::elective
CC4("CC"):::elective
CC5("CC"):::elective
CC6("CC"):::elective

click CMPE150 href "/undergraduate/courses/cmpe150" "Course"
click CMPE160 href "/undergraduate/courses/cmpe160" "Course"
click CMPE220 href "/undergraduate/courses/cmpe220" "Course"
click CMPE230 href "/undergraduate/courses/cmpe230" "Course"
click CMPE240 href "/undergraduate/courses/cmpe240" "Course"
click CMPE250 href "/undergraduate/courses/cmpe250" "Course"
click CMPE260 href "/undergraduate/courses/cmpe260" "Course"
click CMPE300 href "/undergraduate/courses/cmpe300" "Course"
click CMPE321 href "/undergraduate/courses/cmpe321" "Course"
click CMPE322 href "/undergraduate/courses/cmpe322" "Course"
click CMPE343 href "/undergraduate/courses/cmpe343" "Course"
click CMPE344 href "/undergraduate/courses/cmpe344" "Course"
click CMPE350 href "/undergraduate/courses/cmpe350" "Course"
click CMPE352 href "/undergraduate/courses/cmpe352" "Course"
click CMPE362 href "/undergraduate/courses/cmpe362" "Course"
click CMPE443 href "/undergraduate/courses/cmpe443" "Course"
click CMPE451 href "/undergraduate/courses/cmpe451" "Course"
click CMPE492 href "/undergraduate/courses/cmpe492" "Course"

click CC1 href "/undergraduate/electives" "Undergraduate Electives"
click CC2 href "/undergraduate/electives" "Undergraduate Electives"
click CC3 href "/undergraduate/electives" "Undergraduate Electives"
click CC4 href "/undergraduate/electives" "Undergraduate Electives"
click CC5 href "/undergraduate/electives" "Undergraduate Electives"
click CC6 href "/undergraduate/electives" "Undergraduate Electives"

click HSS1 href "/undergraduate/electives" "Undergraduate Electives"
click HSS2 href "/undergraduate/electives" "Undergraduate Electives"
```

## Course Plan

<!-- prettier-ignore-start -->
{{< table class="table-hover table-sm" >}}
||
|:-- |:----------- |:-:|:---:|
| <h4>First Semester</h4>|
| **Code** |**Course Title** |**Credits**|**Notes**|
| MATH101 | Calculus I | 4 ||
| PHYS121 | Introductory Mechanics & Thermodynamics |4 ||
| CHEM105 | Fundamentals of Chemistry |4||
| [CMPE150](/undergraduate/courses/cmpe150) | Introducution to Computing |3||
| EC101 | Principles of Microeconomics |3||
||| 18 ||
| <h4>Second Semester</h4>|
| **Code** |**Course Title** |**Credits**|**Notes**|
| MATH102 | Calculus II | 4 ||
| PHYS201 | Physics III | 4 ||
| HSS | Humanities and Social Sciences (Elective)| 3-4 ||
| [CMPE160](/undergraduate/courses/cmpe160) | Introduction to Object Oriented Programming | 4 ||
| EC102 | Principles of Macroeconomics | 3 ||
||| 18-19 ||
| <h4>Third Semester</h4>|
| **Code** |**Course Title** |**Credits**|**Notes**|
| MATH201 | Matrix Theory | 4 ||
| PHYS202 | Physics IV | 4 ||
| EE210 | Introduction to Electrical Engineering | 3||
| [CMPE220](/undergraduate/courses/cmpe220) | Discrete Computational Structures | 3||
| [CMPE250](/undergraduate/courses/cmpe250) | Data Structures and Algorithms | 4||
| TK221 | Turkish for Native Speakers I | 2 | a |
||| 20 ||
| <h4>Fourth Semester</h4>|
| **Code** |**Course Title** |**Credits**|**Notes**|
| MATH202 | Differential Equations | 4 ||
| EE212 | Introduction to Electronic Engineering | 3 ||
| [CMPE230](/undergraduate/courses/cmpe230) | Systems Programming | 4 ||
| [CMPE240](/undergraduate/courses/cmpe240) | Digital Systems | 4 ||
| [CMPE260](/undergraduate/courses/cmpe260) | Principles of Programming Languages | 3 ||
| TK222 | Turkish for Native Speakers II | 2 | a |
||| 20 ||
| <h4>Fifth Semester</h4>|
| **Code** |**Course Title** |**Credits**|**Notes**|
| MATH202 | Differential Equations | 4 ||
| EE212 | Introduction to Electronic Engineering | 3 ||
| [CMPE230](/undergraduate/courses/cmpe230) | Systems Programming | 4 ||
| [CMPE240](/undergraduate/courses/cmpe240) | Digital Systems | 4 ||
| [CMPE260](/undergraduate/courses/cmpe260) | Principles of Programming Languages | 3 ||
| TK222 | Turkish for Native Speakers II | 2 ||
||| 20 ||
| <h4>Sixth Semester</h4>|
| **Code** |**Course Title** |**Credits**|**Notes**|
| [CMPE321](/undergraduate/courses/cmpe321) | Introduction to Database Systems | 4 ||
| [CMPE350](/undergraduate/courses/cmpe350) | Formal Languages and Automata Theory | 3 ||
| [CMPE352](/undergraduate/courses/cmpe352) | Fundamentals of Software Engineering | 2 ||
| [CMPE362](/undergraduate/courses/cmpe362) | Introduction to Signal Processing | 3 ||
| IE306 | Systems Simulation | 4 ||
| HTR312 | History of the Turkish Republic II | 2 ||
||| 18 ||
| <h4>Seventh Semester</h4>|
| **Code** |**Course Title** |**Credits**|**Notes**|
| [**CMPE443**](/undergraduate/courses/cmpe443) | Principles of Embedded Systems Design | 4 ||
| [**CMPE451**](/undergraduate/courses/cmpe451) | Project Development in Software Engineering | 2 ||
| CC | Complemetary Course (Elective) | 3-4 ||
| CC | Complemetary Course (Elective) | 3-4 ||
| CC | Complemetary Course (Elective) | 3-4 ||
||| 15-18 ||
| <h4>Eighth Semester</h4>|
| **Code** |**Course Title** |**Credits**|**Notes**|
| CMPE492 | Computer Engineering Design Project | 4 ||
| HSS | Humanities and Social Sciences (Elective) | 3-4 ||
| CC | Complemetary Course (Elective) | 3-4 ||
| CC | Complemetary Course (Elective) | 3-4 ||
| CC | Complemetary Course (Elective) | 3-4 ||
{{< /table >}}
<!-- prettier-ignore-end -->

## Notes

<!-- prettier-ignore-start -->
{{< table class="table-hover table-sm" >}}
||
|:-- |:----------- |:-:|:---:|
| a | |
{{< /table >}}
<!-- prettier-ignore-end -->

## Committee

{{< people tag="curriculum" >}}
