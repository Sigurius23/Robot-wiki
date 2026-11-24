# Navigation & social-safety benchmarks for humanoid / Unitree G1 systems

**Review date:** 24 November 2026  
**Scope:** Best currently relevant evaluation benchmarks for navigation and social safety in humanoid/G1 systems, while separating (1) direct biped evidence, (2) simulated social-navigation coverage, and (3) real-world robot validation. This is a use-case shortlist, not a claim to have read every navigation benchmark ever published.

## Verdict in brief

There is **no single best benchmark for everything**. For a G1 program, use a small portfolio:

1. **HumanoidVLN** as the broadest currently relevant starting point for physics-grounded, language-guided navigation with multiple humanoid embodiments and some direct G1 evidence.
2. **“What the Elevation Map Cannot See”** as a targeted G1 hazard-contact / robustness / command–execution mismatch test. Its whole-body locomotion has physical G1 experiments, but the language-navigation evaluation is still simulation-only.
3. **HA-VLN or DPed-VLN** for dynamic-human and social-safety stress tests; both are valuable simulated benchmarks, not G1 validation. HA-VLN additionally reports real robot trials, but on a **Go2 quadruped**, not a G1.
4. **SidewalkBench** for hard sidewalk-specific pedestrian interactions, crossings, and long routes; it is not humanoid-specific.
5. **OmniNavBench** for composite, multi-skill and cross-morphology generalization; **VLN-PE** for physically grounded cross-embodiment VLN; **NavVerse** for indoor-to-outdoor continuity. These broaden coverage but do not replace a humanoid-specific or social-safety suite.
6. Require a **separate real-hardware G1 protocol** for stability, falls, contact safety, and human comfort. Mobile-robot or simulated results cannot establish these.

### At-a-glance shortlist

| Evaluation need | Best fit | Evidence class | Key limitation |
|---|---|---|---|
| G1 embodied VLN / route-following | [HumanoidVLN](https://arxiv.org/html/2608.12860v1); [VLN-PE](https://arxiv.org/html/2507.13019) | Humanoid physics simulation; HumanoidVLN includes a small G1 sim-to-real pilot | No broad real-world G1 reliability evidence; VLN-PE’s physical validation is not a comprehensive social-safety study |
| Hidden/subtle hazards, falls, command-execution drift | [What the Elevation Map Cannot See](https://arxiv.org/html/2610.07396v2) | Direct G1 locomotion hardware tests; navigation evaluation in sim | Complete end-to-end VLN + locomotion navigation not yet validated on hardware |
| Dynamic pedestrians / language-grounded social navigation | [HA-VLN](https://arxiv.org/html/2503.14229v2), [DPed-VLN](https://arxiv.org/html/2609.21504v1) | Rich simulation; HA-VLN also physical Go2 trials | Neither gives direct G1 social-navigation validation; human/path models and collision definitions matter |
| Sidewalk crossings, gestures, long-horizon pedestrian reaction | [SidewalkBench](https://arxiv.org/html/2606.16953v2) | Simulated urban sidewalk evaluation plus limited real trials reported for fine-tuned policy | Not a humanoid benchmark; selected real trials are narrow and do not establish broad deployment safety |
| Many navigation skills in one episode / cross-embodiment | [OmniNavBench](https://arxiv.org/html/2605.09441v1) | Isaac Sim, H1 plus quadruped and wheeled agents | Baseline performance is very low; human motion is deterministic/predefined; no physical-robot validation established |
| Indoor-to-outdoor continuity and urban place goals | [NavVerse](https://arxiv.org/html/2607.19695v1) | Physics simulation, mainly Spot plus Turtlebot experiments | Humanoid/biped interface is supported in principle but not experimentally evaluated; limited pedestrians |
| Real-world human comfort / social controller comparison | [RESONATE](https://arxiv.org/abs/2611.02937) | 320 physical Jackal runs, motion capture and participant ratings | Wheeled Jackal, not biped; valuable protocol template, not G1 proof |
| Sensitivity to pedestrian simulator / driver | [PEDS](https://pedsral26.github.io/) | Modular closed-loop social-navigation benchmark | Only project-page level was reviewed here; detailed protocol/results not audited in this pass |
| Scalable pedestrian simulation / policy training | [NavIsaacLab](https://arxiv.org/html/2606.26265v1) | GPU-parallel Isaac Lab; physical Scout Mini validation | Mobile base, not humanoid/G1 evidence |

## Benchmark-by-benchmark assessment

### A. Direct humanoid / G1 relevance

#### 1. HumanoidVLN — best broad starting point for humanoid VLN

[Paper](https://arxiv.org/html/2608.12860v1)

- Physics-grounded simulator and benchmark with **933 episodes, 87 scenes, and four embodiments**, including Unitree G1.
- Measures language-guided route completion alongside physical embodiment effects such as fall rate, rather than evaluating a nonphysical viewpoint-hopping agent alone.
- Reports a **20-episode G1 sim-to-real pilot** for DualVLN, with episode-level correlation *r*=0.935, mean absolute navigation-error difference 0.68 m, and paired nDTW 0.782±0.188. This is useful initial predictive evidence, **not a large validation study**.
- Aggregate reported JanusVLN mean SR is 43.55% and nDTW 48.38% across embodiments; fall rates vary substantially by robot and model. This makes per-embodiment reporting essential.
- **Recommendation:** use it for a broad baseline on humanoid VLN, and report G1 results separately from H1/other bodies. Add targeted perturbation and hardware tests rather than treating the 20-episode pilot as proof of general sim-to-real transfer.

#### 2. “What the Elevation Map Cannot See” — best targeted G1 hazard/execution stress test

[Paper](https://arxiv.org/html/2610.07396v2)

- Specifically tests geometric-visible, elevation-ambiguous and elevation-invisible floor hazards, external disturbances, falls, and the gap between a high-level waypoint and realized humanoid motion.
- In simulation, its semantic branch raises Safe SR by 3.34–12.26 percentage points across four reported conditions. Anti-deviation feedback raises Safe SR from 11.98% to 23.68%, SR from 19.50% to 29.80%, and reduces collision rate from 35.93% to 12.26% in the reported ablation.
- The RGB-D locomotion policy is physically tested on a Unitree G1 across plastic flooring, wooden boards, and a waterproof plastic sheet. There are **five trials per method per surface**, so real-world numbers are small and setup-specific.
- Crucial scope caveat: **VLN navigation itself is simulated**; the authors explicitly leave full navigation-stack hardware validation for future work. Do not describe it as physical G1 end-to-end navigation validation.
- **Recommendation:** use its hazard taxonomy and measures (hazard contact/intrusion, falls, completion, progress, command tracking) as a complement to HumanoidVLN—not as a replacement for broad route/task coverage.

#### 3. VLN-PE — strong physically grounded cross-embodiment comparison

[Paper](https://arxiv.org/html/2507.13019v1)

- Isaac Sim VLN platform designed around physical robot execution and supporting H1/G1 alongside quadruped and wheeled embodiments.
- Particularly useful for studying embodiment and camera-height sensitivity, transfer gaps, and the importance of robot-specific data. Reported H1 transfers from idealized VLN-CE show substantial success-rate losses (examples in the paper are roughly 10–18 percentage points for cited models).
- **Recommendation:** pair with HumanoidVLN when comparing perception/planning models across embodiment and physical execution. Treat its transfer studies as distinct from real G1 social-safety or whole-body stability validation.

#### 4. HumanoidBench — useful adjacent control baseline, not a navigation benchmark

[RSS paper](https://arxiv.org/abs/2403.10506) · [RSS proceedings page](https://www.roboticsproceedings.org/rss20/p061.html)

- Evaluates simulated humanoid whole-body locomotion/manipulation capabilities, but does not provide language-guided navigation or social-navigation coverage in the cited benchmark comparison.
- **Use only as a complement** for locomotion/control capability; it cannot stand in for route following, crowd behavior, or hazard-aware navigation.

### B. Social and pedestrian navigation

#### 5. HA-VLN — strongest human-aware VLN suite with a physical-robot complement

[Paper](https://arxiv.org/html/2503.14229v2) · [Project and benchmark resources](https://ha-vln-project.vercel.app/)

- Combines continuous and discrete VLN, dynamic multi-human scenes, human-centric instructions and personal-space/collision metrics. HA-R2R includes **16,844 instructions across 90 building scans**; the test set has 3,408 instructions across 18 withheld buildings.
- In its continuous test split, BEVBert’s reported SR is 0.21 when trained on HA-VLN versus 0.15 zero-shot from VLN-CE; the authors show performance falls sharply under dynamic-human challenge relative to ordinary VLN.
- Physical trials use a **Unitree Go2-EDU quadruped**, with 2–4 free-moving volunteers in four indoor settings. Human presence lowers success; abrupt movement and tight corridors still cause collisions. This is real-world social-navigation evidence, but **not humanoid G1 evidence**.
- Important metric caveat: its paper defines success as reaching the goal with zero collisions, while collision metrics also use specific human-zone and per-step formulations. Compare only after matching definitions and action step sizes.
- **Recommendation:** best of this set for human-referenced instructions, dynamic multi-person simulation, and a transferable real-robot trial protocol. Use it to evaluate the social/task layer separately from G1 foot placement and balance.

#### 6. DPed-VLN — best focused paired test of pedestrian awareness

[Paper](https://arxiv.org/html/2609.21504v1)

- Habitat 3.0 benchmark with **33,093 episodes**, ORCA-controlled pedestrians, and paired instruction conditions: route instructions alone versus explicit pedestrian-prior language.
- Reports task success and social-safety outcomes together; the review audit found zero-shot collision rates rise substantially for some models when pedestrians move rather than stay static. For example, NaVILA’s reported collision rate increases from 2.11% to 40.17% in one level-1 comparison.
- Its DPet-RL success/safety trade-off is instructive: higher route success does not imply low human-collision risk. In the best level-1 row noted in the paper audit, human collision rate is 42.45%.
- **Limitations:** wheeled/Spot-like platform rather than a G1 biped; pedestrian paths are generated with ORCA and the expert uses hand-designed clearance rules.
- **Recommendation:** use its paired language conditions and report success, personal-space compliance and collisions together. Do not call its policies or results G1 validated.

#### 7. SidewalkBench — best sidewalk-specific stress suite

[Paper](https://arxiv.org/html/2606.16953v2)

- Covers procedural and scanned sidewalk environments, unit tests, pedestrian-reactive tests, and longer routes; useful because outdoor pedestrian behavior and narrow sidewalk interaction differ from indoor VLN.
- Reported average success is especially low for difficult crossing and gesturing scenarios (3.8% and 9.2% across models in the reviewed results). Its selected FlowPilot synthetic fine-tuning experiments improve crossing and gesturing results in simulation and a small set of real trials.
- **Limitations:** not humanoid-specific; procedural pedestrian behaviors are rule-based; fine-tuning demonstrations are narrow and should not be generalized to broad deployment safety.
- **Recommendation:** use for sidewalk policy stress testing, especially if your G1 deployment includes urban sidewalks. It is a complement, not direct G1 evidence.

#### 8. PEDS — useful for testing whether social-navigation rankings depend on the crowd model

[Project page](https://pedsral26.github.io/) · [Dataset](https://huggingface.co/datasets/arena-rosnav/PEDS37)

- A closed-loop social-navigation benchmark whose distinctive value is comparing across pedestrian behavior models/drivers. This matters because a policy ranking under one pedestrian simulator may not persist under another.
- In this review, the project page was checked but the detailed paper protocol, sample sizes and results were **not fully audited**. Treat as a promising evaluation axis, not as an established numerical benchmark recommendation.

#### 9. RESONATE — best real-world social-navigation comparison protocol in this set

[Paper](https://arxiv.org/abs/2611.02937) · [Dataset](https://zenodo.org/records/23763544)

- Real-world Clearpath Jackal testbed, with eight social-interaction scenarios, eight controller configurations, five repetitions per setting and **320 physical runs**. Uses Vicon trajectory ground truth and combines navigation/social metrics with participant ratings.
- Its results reveal scenario-dependent trade-offs; it is a useful example of reproducible real-robot comparison, objective trajectory measurement and human-centered evaluation.
- **Limitations:** the platform is a wheeled Jackal, not a biped. Its collision and comfort outcomes cannot demonstrate G1 fall resistance, foot-level safety or balance under contact.
- **Recommendation:** borrow the protocol design—scenario matrix, repetitions, trajectory ground truth, participant ratings—for a separate G1 study, but do not directly transfer performance claims.

#### 10. NavIsaacLab — valuable scalable crowd simulator and training substrate

[Paper](https://arxiv.org/html/2606.26265v1)

- Isaac Lab crowd simulation uses diffusion-generated pedestrian trajectories with AMP-style locomotion, GPU-parallel simulation and a human-aware navigation policy. The paper reports 88.67% success for its diffusion+AMP condition versus 74.24% for SFM+AMP in its evaluation.
- **Limitations:** experiments are on a mobile base; physical validation is limited to two Scout Mini scenarios. This does not establish G1 navigation, biped stability or whole-body safety.
- **Recommendation:** consider it for scalable crowd-policy development and sensitivity testing, not as G1 validation.

### C. General-purpose and environment-coverage benchmarks

#### 11. OmniNavBench — best composite multi-skill / cross-morphology challenge

[Paper](https://arxiv.org/html/2605.09441v1) · [Code/project](https://github.com/AutoLab-SAI-SJTU/OmniNavBench)

- Isaac Sim platform with 170 environments and humanoid H1, Aliengo quadruped and Carter wheeled platforms. Its 1,779 human-teleoperated trajectories and 7,116 instruction variants compose PointNav, VLN, ObjectNav, SocialNav, HumanFollow and EQA-like constraints.
- Useful for testing strategy switches and whether an agent can sustain several different tasks in one episode, rather than scoring isolated skills. Its reference behavior is human teleoperated rather than simply shortest-path generated.
- A warning from its own baseline results: full composite success is very low (best reported base-model SR is 8.74% on Aliengo; the paper reports even weaker H1 results and high fall rates). Its dynamic humans follow deterministic predefined trajectories, and no physical robot validation was identified.
- **Recommendation:** best broad stress test for cross-task and embodiment generalization, but interpret failures with subgoal progress and failure categories; do not use raw SR alone to rank policies or infer real G1 readiness.

#### 12. VLNVerse — broad full-physics indoor VLN taskonomy

[Paper](https://arxiv.org/html/2512.19021v1) · [Project](https://sihaoevery.github.io/vlnverse/)

- Full-physics Isaac Sim benchmark designed to unify several VLN taskonomies and support large-scale interactive scenes and flexible embodiments.
- Useful as a broad environment/task complement where language navigation is central. It is not specifically designed around humanoid safety or social navigation.
- **Recommendation:** use when general VLN breadth or task-taxonomy comparisons matter; pair it with a G1-specific test for balance/hazards and a social benchmark for humans.

#### 13. NavVerse — best indoor/outdoor and boundary-transition coverage

[Paper](https://arxiv.org/html/2607.19695v1) · [Project](https://umich-curly.github.io/NavVerse-Benchmark/)

- 200 scenes and 10,000 ObjNav, PlaceNav and VLN episodes across indoor, outdoor and connected indoor-to-outdoor settings, with physics-enabled execution and success, efficiency and safety diagnostics.
- The benchmark exposes exit-finding and post-exit adaptation as distinct failure modes. In its reported zero-shot evaluations, performance is low, including 3.64% PlaceNav SR for the leading VLA in indoor-to-outdoor episodes.
- **Limitation:** the paper’s main experiments use Spot and also a Turtlebot comparison; although the interface is intended to support humanoids, additional biped/humanoid embodiments are **not experimentally evaluated**. Its authors also identify limited pedestrian/interactive-agent dynamics.
- **Recommendation:** use if a G1 must traverse building-to-street transitions, but port/validate a biped embodiment and add pedestrians and biped-specific stability measures before drawing G1 conclusions.

#### 14. LHPR-VLN — long-horizon instruction/reasoning complement

[Paper](https://arxiv.org/html/2412.09082v1)

- 3,260 long-horizon tasks averaging about 150 task steps; its independent/conditional success measures help separate subtask completion from whole-episode completion.
- Valuable for language/task-memory stress testing, but it is not a biped locomotion or social-safety benchmark.
- **Recommendation:** add only when long-sequence reasoning and subgoal memory are explicit evaluation priorities.

## What “real-world validated” means in this review

These categories should not be collapsed:

- **Direct physical G1 evidence:** the G1 hazard paper tests locomotion on physical G1, but its complete VLN navigation remains simulated. HumanoidVLN reports a 20-episode G1 pilot, which is promising but small.
- **Physical social-navigation evidence on a different robot:** HA-VLN uses Go2 quadruped; RESONATE uses a wheeled Jackal. They are meaningful real-robot evidence for those respective systems, not proof for G1.
- **Simulation-only or no relevant physical validation identified:** DPed-VLN, OmniNavBench, VLNVerse, SidewalkBench as a benchmark platform, and NavVerse’s humanoid capability. SidewalkBench has limited real trials for selected fine-tuned policies; that does not validate the benchmark broadly on a humanoid.
- **Mobile-base training / validation:** NavIsaacLab uses a mobile base and Scout Mini; it is not biped evidence.

## Recommended G1 evaluation battery

For a credible report card, run a fixed, versioned battery rather than declaring a single benchmark score:

1. **Route/VLN:** HumanoidVLN and a VLN-PE-style physical execution comparison. Report G1 results separately, with scene-disjoint evaluation and clear route/instruction definitions.
2. **Biped hazards and robustness:** adapt the hazard taxonomy from “What the Elevation Map Cannot See”; include visible/ambiguous/invisible hazards, stairs/uneven terrain, pushes/payload/sensor perturbations, command-vs-realized pose error and repeatability.
3. **Dynamic people:** use HA-VLN or DPed-VLN for reproducible simulation; add SidewalkBench if sidewalk use is expected. Evaluate multiple pedestrian drivers (PEDS-style sensitivity check) rather than relying on one scripted crowd model.
4. **Composite and long-horizon ability:** use selected OmniNavBench and LHPR-VLN tasks; separately inspect each subgoal, return-to-start, early stops and falls.
5. **Real G1 social validation:** conduct staged tests with consenting participants, beginning with controlled empty corridors and increasing density. Measure minimum/personal-space distance, near misses, yielding/stopping, route completion, falls, foot contacts, speed, recovery, and participant comfort. Keep a conservative safety stop and predefine abort rules. A small pilot is feasibility evidence, not a reliability claim.

### Minimum reporting set

Always report, with denominators and confidence intervals where practical:

- task success and subgoal completion;
- route/path efficiency and progress;
- collision/contact rate, separated into human, environment and semantic-hazard contact;
- fall and recovery rate;
- social distance distribution (not just a single collision flag), near-miss and yielding behavior;
- commanded-versus-realized pose/heading error and waypoint tracking;
- performance by embodiment, crowd density, scene split and perturbation level;
- simulator pedestrian model, deterministic/randomized motion protocol, and exact collision/goal definitions;
- physical-robot trial count, participant exposure, and safety interventions.

**Do not treat a wheeled robot’s social-navigation score as evidence for G1 balance, fall resistance, bipedal foot placement or whole-body collision safety.** Nor should simulation contact checks alone be treated as human comfort or injury-risk measurements.

## Sources and review coverage

Primary sources linked inline above. Full available HTML papers/results reviewed in this pass include: the G1 semantic-hazard/execution benchmark, OmniNavBench, NavVerse, and HA-VLN. HumanoidVLN, SidewalkBench and NavIsaacLab were fully reviewed in the preceding benchmark pass recorded in session memory. RESONATE paper/project materials were reviewed. VLN-PE and VLNVerse were assessed from their primary paper pages. PEDS was project-page screened only. DPed-VLN was fully read in the separate [G1 navigation paper audit](G1_navigation_paper_audit.md). This coverage is broad for relevant candidates, but not literally every navigation or social-navigation benchmark.

## Expanded social-navigation landscape: mature baselines and evaluation dimensions

The shortlist above prioritizes humanoid relevance and newer benchmark platforms. For a more complete social-navigation evaluation, include established ROS/simulation frameworks and report pedestrian burden—not only robot collisions. They are predominantly mobile-robot benchmarks, so use them as methodology/context rather than as G1 evidence.

### 15. SocNavBench — grounded replay benchmark with pedestrian-impact metrics

[ACM paper](https://dl.acm.org/doi/10.1145/3476413) · [Code](https://github.com/CMU-TBD/SocNavBench)

- Simulation framework with photorealistic capability and 33 curated scenarios based on real-world pedestrian trajectories, enabling repeatable comparison.
- Its metric suite covers task success/failure, path and motion quality, closest pedestrian distance and time-to-collision; importantly, it also considers pedestrian disruption and path deviation, rather than reducing “social” performance to zero collision alone.
- The key methodological caveat is **replay rather than closed-loop human response**: recorded pedestrian trajectories do not adapt to the robot’s actions. The benchmark authors themselves note that this makes human reaction to the robot difficult to represent.
- **Use it for:** replayable, grounded scenario comparison and pedestrian-path disruption metrics. **Do not use it alone** to claim that a robot behaves well with reactive people.

### 16. SEAN 2.0 / SEANavBench — structured social situations and ROS planner comparison

[SEAN 2.0 paper (DOI)](https://doi.org/10.1109/LRA.2022.3196783) · [Project/docs](https://sean.interactive-machines.com/about/publications/)

- A ROS-oriented framework for formalizing and generating canonical social situations, useful for standardized testing of local planners under configurable pedestrian scenarios.
- SEANavBench combines SocNavBench scenarios with the SEAN 2.0 simulation stack for challenge-style comparison.
- **Limitations:** simulated pedestrians and benchmark-specific dynamics; not a biped benchmark or physical human-comfort test. Treat it as a reproducible scenario/protocol layer, and document the exact simulator and driver versions used.

### 17. HuNavSim 2.0 — ROS 2 human-behavior simulator and metrics toolkit

[HuNavSim 2.0 paper/project](https://github.com/robotics-upo/hunav_sim)

- ROS 2 software for simulating varied human-agent navigation behavior, designed to run with general robotics simulators such as Gazebo or Isaac Sim. The updated toolkit reports a broad collection of social-navigation metrics (32 in its paper description) and supports multiple human behavior configurations.
- It is useful when you need to vary behavior models and integrate social scenarios into a robot simulation stack. This is more a reusable **simulator/toolbox** than one fixed, universally accepted benchmark dataset/leaderboard.
- **Limitations:** simulated behavior is still a model choice; validate human-motion fidelity and avoid equating the number of available metrics with their construct validity. Not G1-specific.

### 18. Arena-Bench — highly dynamic obstacle/social navigation planner suite

[Arena-Bench paper (DOI)](https://doi.org/10.1109/LRA.2022.3190086) · [Project/code](https://github.com/ignc-research/arena-rosnav)

- Provides a suite to train/test navigation planners in dynamic environments, with standardized scenarios and ROS integration. Often useful for planner baselines and stress tests where crowds or moving obstacles matter.
- Related benchmark comparisons note simplified pedestrian speed profiles in some configurations (e.g. constant-speed agents), so scenario variety should not be confused with realistic population diversity.
- **Use it for:** a reproducible ROS planner comparison or dynamic-obstacle regression suite. Add stronger social behavior diversity and report burden/comfort separately if evaluating social compliance. It is not a humanoid benchmark.

### 19. PopNavShift — strongest new test of population-model sensitivity

[Paper](https://arxiv.org/html/2609.21838v1)

- A matched simulation framework that varies pedestrian behavior populations while keeping the robot controllers and physical encounter fixed. It tests eight behavioral-population conditions, three robot strategies and 7,488 matched robot runs.
- The central result is that ranking instability is larger for pedestrian burden than robot travel time: in its matched time-pressure intervention, mean and worst-decile pedestrian-delay rankings reverse in 22.4% and 23.9% of comparable cells versus 8.6% for robot travel time. Across population pairs, the corresponding reversal rates are 25.8%, 24.8%, and 8.7%.
- **Important limitation:** personas and their responses are synthetic; the response-to-motion mapping is not fitted to joint observations of those individuals and their trajectories. The robot is a differential-drive disk with perfect local state, and pedestrian agents do not represent full human or group complexity. These results motivate a sensitivity test; they do not estimate population-wide real-human effects.
- **Use it for:** an evaluation-design lesson—rerun policies against several behavior drivers/populations, include worst-decile human burden and robot metrics, and check ranking stability. Do not transplant its synthetic population values as real demographic facts.

### 20. Principles and Guidelines for Evaluating Social Robot Navigation Algorithms

[ACM survey/guidelines](https://dl.acm.org/doi/10.1145/3700599)

- A useful methodological companion rather than a benchmark: surveys social-navigation scenarios, testbeds and metrics, and emphasizes evaluation context, reproducibility and multiple social dimensions.
- The practical implication for a G1 effort is to publish the robot morphology/control stack, crowd model, scenario set, participant protocol, metric definitions and failure handling. Benchmark names alone do not ensure comparability.

### Data resources that should not be mislabeled as executable benchmarks

- **SCAND**, **THÖR** and **THÖR-MAGNI** provide real human/robot trajectory data and can help ground models or offline analyses. They are not interchangeable with a closed-loop benchmark in which a policy is tested and people respond to it.
- **PEDS-37** is a dataset release accompanying PEDS; it enables analysis and reproducibility but the benchmark contribution is the matched multi-driver evaluation protocol.
- Trajectory datasets are valuable test inputs; they do not by themselves establish real-time policy safety or personal comfort.

## Updated practical recommendation: layered benchmark stack

For the most defensible G1 study, combine **one benchmark per question**, not one overall rank:

| Layer | Recommended starting point | Additional cross-check | What the result can support |
|---|---|---|---|
| Biped VLN and body-specific locomotion | HumanoidVLN | VLN-PE | Simulated route-following across humanoid embodiment; small pilot evidence for sim-real correlation |
| G1 hazards, perturbations, command/execution alignment | Elevation-map-cannot-see hazard taxonomy | Add independently designed perturbation/fall tests | Targeted G1 locomotion robustness; not yet full physical VLN validation |
| Human-aware language navigation | HA-VLN or DPed-VLN | SidewalkBench for outdoor settings | Simulated social interaction; HA-VLN provides a Go2 physical protocol, not G1 proof |
| Pedestrian behavior sensitivity | PEDS, plus PopNavShift-style paired runs | HuNavSim / SEAN 2.0 driver variations | Whether policy rankings depend on the simulated crowd assumptions |
| Grounded trajectory impact / repeatable scenarios | SocNavBench | Human-subject trials | Replay-based pedestrian disruption, not reactive-person comfort |
| Real human-centered mobile navigation methods | RESONATE protocol | HA-VLN physical protocol | A template for trials and user measures on their tested platforms |
| Mixed tasks / city transition | OmniNavBench and NavVerse | LHPR-VLN for long sequence reasoning | Broad simulated task coverage; humanoid and social validity must be added/verified |

**Non-negotiable:** report G1 results separately; define contact, near miss, safe-distance and success thresholds before testing; include falls and foot contacts; report both average and tail human-burden outcomes; and run more than one pedestrian model. For physical tests, state trial counts and participant conditions and avoid making population-level comfort claims from small controlled pilots.
