# outram-park
Open-source Unified TRAnsient Multi-Physics Advanced Reactor simulation Kit (OUTRAM PARK)

# Purpose 

This repository is meant for students and teachers alike who want to learn 
about nuclear reactors and their safety aspects.

When wanting to communicate about the safety aspects of nuclear reactors,
there is difficulty as things may be quite abstract. In fact, trying to 
talk about things like thermal hydraulics, neutronics and material sciences
may be quite inaccessible to the layman. 

Communicating these concepts effectively is essential for nuclear science 
education. This was done for simulators such as the dalton-nuclear-simulator:

```
https://playgen.com/play/dalton-nuclear-simulator/
```

However, these simulations may not be quite realistic. Nor is the source code 
available.

outram-park aims to deliver realisitic simulations based on the proper 
neutronics, thermal hydraulics and material science equations, while at the 
same time, enabling students and teachers alike to interact with these.



# How it started

It started as a sketch. An early concept from 2025, drawn by hand on graph
paper, titled **"Natural FHR Simulator, Mark I"**: a fluoride-salt-cooled
high-temperature reactor (FHR) you could watch and operate.

![Hand-drawn 2025 concept sketch of the Natural FHR Simulator Mark I: a pebble-bed core with control rod, graphite reflector and decay-heat removal loop; a primary salt pump labelled TUAS; an intermediate salt-to-salt heat exchanger; a helical steam generator, single-stage expansion turbine and condenser labelled TAMPINES](docs/images/fhr-simulator-mark-i-concept-2025.jpg)

Everything on that page was a question for code to answer. On the left, the
core: a pebble bed with a temperature-sensitive display, a control rod, a
graphite reflector and a decay-heat removal loop. In the middle, a primary
salt pump driving the salt through an intermediate salt-to-salt heat
exchanger. On the right, a helical steam generator feeding a single-stage
expansion turbine and a condenser. The sketch is honest about what it left
out: "no HP, LP turbine for simplicity", and a primary pump that "really has
parallel but simplify".

Two labels on it already name the pieces that would carry the idea: **TUAS**
under the salt loops, and **TAMPINES** under the steam side. Both are crates in
[`outram-park-backend`](https://github.com/theodoreOnzGit/outram-park-backend)
today (`tuas_boussinesq_solver` and `tampines`), and the rest of OUTRAM PARK
grew around them.

# Contents

This repository contains

1. ~~Finished simulators for four thermal spectrum reactor types. HTGR, BWRs,
PWRs, and FHRs.~~ **Corrected 2026-10-03: no simulator is finished yet.**
   - **Here, placeholders only:** `outram-park/src/{htgr,fhr,bwr,ipwr,gen_3_conventional_reactor,fukushima}_sim/` are entry points for planned simulators. Each currently only prints "Hello, world!".
   - **The real work so far lives in the backend's digital-twin engine** ([`outram-park-backend/crates/outram-park-digital-twin-engine`](https://github.com/theodoreOnzGit/outram-park-backend/tree/develop/crates/outram-park-digital-twin-engine)):
     - `htgr_sim_v1`: an HTR-10 simulator in development, **not yet validated**;
     - `fhr_sim_v2`: a prototype;
     - `distillation_sim_v1`: a prototype.
   - **There is no BWR or PWR simulator yet.**
2. Presentations for using these simulators to teach reactor concepts.
3. (Planned) a teaching website with lessons, live simulations and code,
   rendered from `outram-park-backend`'s documentation. See
   [the teaching-site epic](https://github.com/theodoreOnzGit/outram-park-backend/issues/509).

# Teaching Content and Context

Nuclear Science outreach presentations are usually aimed at public. These 
can be:

1. Students 
2. Teachers 
3. Workers and Salarymen
4. Policymakers
5. Investors and Businessmen
6. Fathers and Mothers
7. Hobbyists and Science Communicators

Here is an AI generated list of FAQs that may be asked:

```
For students, teachers, and hobbyists/science communicators in the 
Singapore context:

Technical Feasibility Questions:

    How do SMRs differ from traditional reactors? Why are they supposedly "safer"?
    Where would you even put a reactor in land-scarce Singapore? (Offshore? Underground? Pulau Tekong?)
    How does cooling work without large water bodies? Can seawater be used given our maritime location?
    What happens during a malfunction - how does emergency cooling work in an SMR?

Energy Security & Economics:

    How does nuclear compare to solar panels on HDB rooftops and reservoirs?
    Can nuclear work alongside our LNG infrastructure, or is it replacement?
    What's the actual cost per kWh compared to imported natural gas?
    How long does it take to build? (Students know Singapore wants energy solutions fast)
    Do we need to import all the fuel, or is that more secure than importing gas?

Waste & Environmental:

    What happens to nuclear waste in a country with no space for landfills?
    Can we send waste elsewhere, or must we store it here?
    Is nuclear actually "greener" than natural gas for our 2050 carbon goals?
    What about thermal pollution in our already-warm coastal waters?

Singapore-Specific Context:

    Why is the government only "studying" nuclear, not committing? What are they waiting for?
    How does this fit with the Malaysia electricity import plan and regional grid?
    Would we need to train Singaporeans overseas since we have no nuclear program?
    What do neighboring countries (Malaysia, Indonesia) think about Singapore having nuclear?

Safety & Social:

    What if there's an accident - can you even evacuate Singapore? (Entire country is within typical evacuation radius)
    How do you convince Singaporeans living in high-density HDB estates this is safe?
    Who would regulate it - NEA? EMA? A new agency?

```

Once built, the simulators are intended to address only certain questions
from this list.

1. What are SMRs and how do they differ from traditional reactors, why are they safer?
2. Do maritime reactors work?
3. What happens during a malfunction?

The goal of these simulators is to ~~demonstrate the safety of reactors~~
**illustrate passive-safety concepts and accident behaviour for education**,
which means they need to simulate accident scenarios with reasonable accuracy.
They are for education and outreach only, not for licensing, safety
decisions or emergency response (see `outram-park-backend`'s
`RESPONSIBLE_USE.md`).

To do so, we will have presentations, which facilitate simulator use to 
demonstrate passive safety and accident scenario simulations for SMRs.



# Beamer presentations 


Compilation of the presentations would need you to navigate to the 
folder, and use pdflua. For example, in the presentations folder,
the file is st_presentation.tex:

```
latexmk -pvc -pdflua --interaction=nonstopmode st_presentation.tex
```

This uses the midcenturymodern style files, made by Jules LeGuy under 
the CC-BY-4.0 license. His github is here:

```
https://github.com/jules-leguy/midcenturymodern?tab=readme-ov-file
```





