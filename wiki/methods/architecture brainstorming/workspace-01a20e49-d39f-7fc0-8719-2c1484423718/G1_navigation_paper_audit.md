# G1 navigation literature audit — full-paper evidence and model fit

**Audit date:** 24 November 2026  
**Purpose:** Verify the previously surfaced navigation claims against primary papers, read the most relevant papers end-to-end, and expand the model/paper map. This is a literature audit, not a claim that every paper ever published on humanoid navigation has been read.

## Reading-status key

- **Full paper read:** Systematic pass through all available arXiv HTML sections, results, limitations, and appendices where provided.
- **Screened only:** Discovery/abstract/selected sections checked. Useful lead, but claims below are not treated as fully audited.

## Bottom line for a G1 stack

There is no single paper here that supplies all of: long-range goal selection, semantic/social reasoning, traversability-aware biped motion, dynamic obstacle handling, and a defensible safety layer. The most compelling direction is a **composed architecture**:

1. **Goal/task layer:** language or task planner chooses a destination/subgoal; LHNav is the most directly relevant long-horizon G1 example, but its demonstrated task set is small and its navigation policy is trained on single-goal demos.
2. **Navigation prior / local policy:** choose based on the dominant failure mode. RoM-Nav is the strongest directly evidenced candidate for mapless stairs and cross-floor routes. FocusNav is a local G1 policy for mixed terrain/obstacles. EgoNav (human-data paper) is an unusual semantic/multimodal prior for crowds and transparent surfaces, with significant compute and sensor caveats.
3. **Geometric execution:** put a local geometry-aware planner between predicted waypoints and the locomotion controller. The second EgoNav paper demonstrates this pattern on an omnidirectional humanoid-base robot; it is not a Unitree G1 biped evaluation.
4. **Safety cage:** Caging VLN is the most directly composable formal-safety design: a VLM/VLA proposes, while an SDF-based barrier-certified MPPI layer filters motion. Its guarantee is conditional on its planar model, map, robot footprint, state, and execution assumptions; it is not a proof for the full biped dynamics.
5. **Evaluation:** separate route completion, collision/contact, falls, social distance, efficiency, and goal/localization errors. Do not compare reported success rates across papers without matching task definitions, platforms, and trial protocols.

**Practical shortlist:** For a G1 expected to handle stairs and long routes, start from RoM-Nav + a geometric/safety execution layer. Add a semantic task planner only for language/subgoal selection. If crowds/glass are central, evaluate EgoNav’s visual-memory/DINOv3 idea separately rather than assuming it replaces geometric safety. For whole-body natural motion and multiple stops, LHNav is the closest architecture precedent, but it needs a safety cage and broader hardware validation.

---

# Fully read primary papers

## 1. RoM-Nav — mapless, multi-floor G1 navigation

[Learning Safe Humanoid Navigation from Reduced Order Models (arXiv:2609.19272)](https://arxiv.org/html/2609.19272v1) — **Full paper read**

**What it is.** Two-stage RL. First train navigation on a simple reduced-order single-integrator model using 3D LiDAR. Then use the RoM policy to kickstart a policy on full humanoid dynamics with a frozen locomotion controller. An online Poisson safety filter / CBF-QP modifies planar velocity outputs around out-of-distribution obstacles.

**Evidence in paper.** G1 with Livox MID-360 and downward-facing ZED Mini; navigation policy at 5 Hz and locomotion at 50 Hz. The paired simulation test has 1,024 initial conditions. RoM-Nav reports 82.3% success within 45 s and 92.8% within 120 s; the single-stage method reports 62.2% and 81.7%, respectively. The important gain is concentrated in cross-level goals. Hardware examples report up to 100 m path length and 10 m vertical ascent; these exceed the stated training maxima (30 m and 8 m). In controlled hardware obstacle tests, the safety filter reduced collisions from 2/10 to 0/10 for OOD obstacles and 4/10 to 0/10 for adversarial hanging-tube obstacles, with longer time-to-goal.

**Limits / interpretation.** “Mapless” describes the navigation policy input; a separate GLIM map/relocalization system was used to align hardware starts/goals and for analysis. Goals must be accurately specified in a coherent reachable location. LiDAR is explicitly insufficient for glass/transparent obstacles; a glass door/window was physically blocked in one deployment. The planar safety filter can disagree with the learned policy or close a route it considers traversable, and the authors identify whole-body safety as future work. The robust headline is the cross-floor capability—not a general collision-free guarantee.

**G1 fit.** Strongest candidate in this set for stairs, multi-story buildings, and mapless navigation to known metric goals. Require a complementary visual/semantic treatment for glass and an independent whole-body-aware safety strategy.

## 2. FocusNav — local obstacle avoidance plus rough terrain on G1

[FocusNav: Spatial Selective Attention with Waypoint Guidance for Humanoid Local Navigation (arXiv:2601.12790)](https://arxiv.org/html/2601.12790v1) — **Full paper read**

**What it is.** A privileged simulation teacher (GuideOracle) supervises a G1 local controller. The policy fuses LiDAR and depth into a BEV representation, predicts goal-conditioned waypoints backward from the goal, and uses (a) waypoint-guided spatial cross-attention and (b) stability-aware gating that suppresses distant scene information when the robot becomes unstable. A recurrent controller tracks the selected local motion.

**Evidence in paper.** Real G1 is a 29-DoF unit with MID-360 and RealSense D435i; localization uses Fast-LIO. Real tests include 16 cm stairs, 22° slopes, static obstacles, pedestrian interference, and combinations of terrain and obstacles. Fifteen trials are run for each of six configurations. Simulation reports three seeds, each evaluated over 100 randomized episodes. In the hardest dynamic + unstructured simulation case, reported success is 87.02% versus 63.67% for the proprioception-guided cross-attention baseline and 50.32% for the simple fusion baseline. The paper also notes a trade-off: in one dynamic, unstructured simulation setting, FocusNav has a slightly higher collision frequency than WGSCA-only, because the stability gate prioritizes not falling over aggressive obstacle avoidance.

**Limits / interpretation.** Local-navigation policy, not a high-level semantic or long-horizon route planner. Requires both LiDAR and depth. The paper’s own limitations say it focuses forward and lacks robust backward/omnidirectional awareness; it requires predefined goals and lacks high-level semantic reasoning. Real-world comparisons are 15 trials per configuration, so they are evidence of feasibility, not a large reliability study. Baseline naming/results should be read from the paper tables, not treated as a universal ranking.

**G1 fit.** Directly relevant if the stack already has goal generation and needs a terrain-aware local G1 controller. Pair it with a global route/subgoal layer and a separate safety monitor.

## 3. EgoNav — human-walking data as a navigation prior

[Learning Humanoid Navigation from Human Data (arXiv:2604.00416)](https://arxiv.org/html/2604.00416v1) — **Full paper read**

**What it is.** A conditional trajectory-diffusion prior trained on 300 minutes / roughly 25 km of egocentric human walking data, not robot trajectories. It uses a 360° rolling RGB-depth-semantic visual memory plus frozen DINOv3 image features and past 6D trajectory. A receding-horizon controller samples 64 trajectories over 5 seconds, filters static collisions, clusters path modes, and applies a momentum/latency-aware selection rule.

**Evidence in paper.** The reported G1 deployment ran for 37.5 minutes and 1,137 m across static, corridor, glass, and dynamic settings, with 96–99% autonomous time. Intervention rates were 9 static, 1 corridor, 5 glass (11 without DINOv3), and 6 dynamic. The system waited at a closed door, passed between pedestrians, and turned away from glass that depth alone did not capture. Diffusion runs on a Jetson Thor connected to the onboard Orin NX; the deployed loop is about 1.7 Hz with batch size 64 (the abstract calls it real time, but it is not a high-rate locomotion controller).

**Limits / interpretation.** No real-world baseline comparison; the intervention count/autonomous-time figures are not collision-free success rates. Hardware compute includes an external/large Thor module (the paper says it may be carried on the back), and sensing relies on stereo depth plus semantic segmentation. Offline collision scoring uses a point cloud from the same depth-based visual memory, so it cannot fully measure the glass/dynamic benefits that appear in deployment. The learned output is a navigation prior, not task-goal reasoning or a locomotion policy. The authors identify monocular depth and goal-conditioned trajectory selection as future work.

**G1 fit.** A distinctive option for social/crowd context and glass cues. Treat as a candidate prior to a geometry/whole-body controller—not as a standalone certified safety solution.

## 4. SAFER-Nav — segmentation-aware RGB navigation fine-tuning

[SAFER-Nav: Enhancing Safety for Visual Robot Navigation via Segmentation-Aware Fine-Tuning (arXiv:2606.11636)](https://arxiv.org/html/2606.11636v1) — **Full paper read**

**What it is.** Adds a trainable segmentation branch to a frozen ViNT-derived RGB policy. OneFormer floor/traversability masks refine the policy representation, and an auxiliary segmentation-only waypoint branch is blended at inference to bias actions into free space.

**Evidence in paper.** Tests ViNT, NoMaD, CARE-augmented variants, and SAFER-Nav on RoboMaster S1, TurtleBot4, and LoCoBot across two unseen indoor layouts; ten trials per platform/environment. For the teleoperated moving-robot scenarios, SAFER-Nav records 0/10 collisions in both corner-appear and front-approach; ViNT has 5/10 and 9/10, NoMaD 6/10 and 8/10, and CARE variants 2–3/10. Static tests report higher arrival and fewer collisions for SAFER-Nav in the listed conditions.

**Limits / interpretation.** These are small indoor wheeled robots, not a humanoid. It depends on segmentation quality, only tests a limited backbone family, and is not an explicit collision-avoidance or formal safety module. Authors flag delayed or overly conservative avoidance in narrow/cluttered areas and hand-tuned blending parameters. Do not generalize “compatible with diverse backbones” into a demonstrated backbone-agnostic result.

**G1 fit.** An RGB-only safety-aware training idea to borrow/evaluate—not a proven G1 model. Its inference-time segmentation and test-domain assumptions should be profiled on the actual G1 compute/camera pipeline.

## 5. VISTA — action-history conditioning for metric scale consistency

[VISTA: Scale-Aware Visual Navigation via Action History Conditioning (arXiv:2606.17294)](https://arxiv.org/html/2606.17294v1) — **Full paper read, including supplementary methods/results**

**What it is.** Conditions normalized waypoint prediction on recent normalized actions so a visual navigation policy can infer the mapping between its normalized action space and actual physical motion. Uses DINOv3 features and training examples resampled across 2–12 Hz; its aim is to reduce metric/curvature mismatch under changes in robot speed or control frequency.

**Evidence in paper.** Offline scale-consistency tests report lower cross-track error than ViNT/NoMaD across changed observation spacings. Closed-loop comparisons are shown for outdoor (3 trials), forest (5), and office-lab (5), with VISTA completing all listed trials; ViNT/NoMaD/MetricNet have more false goal detections and/or collisions, especially in visually repetitive outdoor/office scenes. Perturbed control-rate/speed tests show VISTA is more robust than ViNT in the tested sharp-turn setup. The supplementary text identifies an Agilex Bunker with AGX Orin as the main quantitative deployment platform. G1 is shown in a deployment figure, but the paper does not provide a comparable G1-specific quantitative table; Spot’s built-in collision avoidance also affects the stair demonstration.

**Limits / interpretation.** The headline “100% goal prediction” is across these small setting-specific trial counts, not a general guarantee. It uses topological maps and external localization/action history. The authors identify limited robot-geometry awareness, ambiguity in visually repetitive consecutive images, and poor scale grounding at very low rates (≤1 Hz). Strongest direct applicability is scale/control-rate robustness; G1 quantitative transfer evidence is limited.

**G1 fit.** Useful for aligning visual waypoint outputs with the G1’s real commanded/executed step length and for detecting control-rate mismatch. It does not solve obstacle geometry or whole-body feasibility.

## 6. LHNav — long-horizon humanoid navigation with whole-body motion tokens

[LHNav: Long-Horizon Humanoid Navigation via Multirate Coordination and Physics-Grounded Action Data (arXiv:2611.12136)](https://arxiv.org/html/2611.12136v1) — **Full paper read**

**What it is.** An asynchronous three-rate architecture: a Brain manages a long-horizon plan and verifies arrival; a Cerebellum predicts visual-language-conditioned whole-body motion tokens plus auxiliary waypoints; a frozen SONIC decoder executes at 50 Hz. The Brain/VLM runs at a slower rate (arrival checks up to 1 Hz; VLA policy around 8 Hz). A simulation data engine generates ARDY routes, tracks them with a privileged SONIC variant, and renders executed motion for VLA training.

**Evidence in paper.** On 522 held-out single-goal simulated episodes, LHNav reports 52.3% success within 0.5 m and 75.7% within 1.5 m, compared with OmniNav’s 36.0% / 69.0%; it also reports lower route violation, jerk, and falls than compared waypoint methods. Long-horizon simulation contains 45 tasks with at least three ordered destinations; the full asynchronous system has 75.6% task success. Removing task management causes 0% success in that setup; removing arrival verification drops it to 55.6%. G1 tests include five trials for each listed home target/condition; the three-destination reading-notes task succeeds 4/5. Reconfigured object layouts achieve 93.3–100% on the listed single-goal target conditions.

**Limits / interpretation.** Real G1 evidence is a small set of household tasks; the long-horizon headline is primarily simulation. The task is visiting target images/regions; the shown simulated “meal” run does not cook or serve. The method relies on a high-capacity VLA/SONIC stack and a rendered data engine, and no independent formal safety guarantee is supplied. The navigation route data and task/decomposition layer are separate components; reported success depends on both.

**G1 fit.** Best match in this set for natural whole-body execution across successive destinations. Use as a high-level motion/task architecture reference, but add explicit geometry/safety and broader tests with real crowds/transparent obstacles.

## 7. Caging VLN — geometry and barrier-certified execution wrapper

[Caging Vision-Language Navigation for Legged Robots via Barrier-Certified Safety Architecture (arXiv:2611.04972)](https://arxiv.org/html/2611.04972v1) — **Full paper read, including theorem/appendix**

**What it is.** A modular semantic-to-physical architecture. A VLM/VLA proposes local discrete goals; a kinematic projector maps them to reachable positions; then low-dimensional Bézier-parameterized MPPI plans using an incrementally updated 2D SDF. A discrete exponential barrier function checks multi-point approximations of the robot footprint; uncertified actions are rejected and a safe backup is applied. Optional JPS provides global route guidance. Grounding-DINO/SAM2 can add object-relative terminal approach.

**Evidence in paper.** Tests on G1 and Ghost Robotics Vision 60. In controlled G1 dEBF trials, no collisions are observed in the 40 enabled trials across static and sudden-obstacle cases, while aggregate collision rates without dEBF are reported as 80% and 100% in the paired test conditions. In 75-trial G1 end-to-end tests, simple/complex success remains 0.75 while collision rate falls from 0.33/0.50 to 0/0. On a larger system-level G1 test, all 60 uncaged trials collide and all 60 caged trials are reported collision-free. Object-centred terminal grounding lowers mean endpoint error from 1.50 m to 0.29 m, but this auxiliary result is on Vision 60.

**Limits / interpretation.** The theorem is conditional: correct planar robot model, valid/current SDF and footprint, safe initial state, feasible safe backup, and exact execution of certified control. The authors explicitly say state-estimation error, latency, tracking error, and unseen geometry are not covered. The planar body-twist safety set is not a proof of whole-body biped stability or foot/arm clearance. Vision-60 collisions persisted when geometry was absent from the map (thin wires, edges, poles, blind spots). Semantic goal correctness remains the front end’s responsibility.

**G1 fit.** Most promising composable safety wrapper here. Port the multi-point footprint to the G1 and validate the SDF and stopping/braking behavior against gait tracking, latency, stairs, arm swing, and moving people before using “guarantee” language.

## 8. DPed-VLN — dynamic-pedestrian VLN benchmark and policy

[DPed-VLN: A Benchmark for Socially Compliant Vision-and-Language Navigation in Dynamic Pedestrian Environments (arXiv:2609.21504)](https://arxiv.org/html/2609.21504v1) — **Full paper read, including appendices**

**What it is.** Habitat 3.0 benchmark with 33,093 episodes, ORCA-controlled humanoid pedestrians, and paired instructions: ordinary route guidance versus an additional explicit pedestrian-prior condition. DPet fuses RGB-D, language, start-relative progress, and auxiliary pedestrian count/position/motion prediction; evaluated with RL and imitation learning.

**Evidence in paper.** DPet-RL obtains 37.13%/38.55% success under the two instruction levels; DPet-IL has lower human collision rates in several comparisons but much lower task success. Zero-shot NaVILA/StreamVLN collision rates increase dramatically when pedestrians move rather than remain static (e.g., NaVILA 2.11% to 40.17% under the reported level-1 setting). Limited LoRA fine-tuning particularly reduces StreamVLN’s collision rate (37.24% to 27.14% for level-1 and 41.59% to 26.06% for level-2), but does not uniformly improve all efficiency metrics.

**Limits / interpretation.** Simulator benchmark and Spot-like wheeled agent, not a G1 deployment. Pedestrian paths use ORCA and the expert uses hand-designed clearance rules. DPet-RL has a clear success/safety trade-off (42.45% human collision rate in its best level-1 row; 36.70% in level-2); “best navigation success” does not mean safest. Its key value is the paired instruction design and joint reporting of success, personal-space compliance, and collision metrics.

**G1 fit.** A useful social stress-test/data design and a warning that language-only “human-aware” claims are not enough. Adapt the test ideas to a G1 biped and measure falls, contact, clearance, and personal space separately.

## 9. GemNav — MLLM-based metric waypoint policy

[GemNav: Discrete-Token Visual Robot Navigation using a Multimodal Large Language Model (arXiv:2607.06882)](https://arxiv.org/html/2607.06882v3) — **Full paper read**

**What it is.** LoRA adapts Gemma 4-E2B-it with a probabilistic categorical representation of metric robot-frame waypoint coordinates; soft decoding recovers continuous waypoints. Training goals are sampled by metric displacement rather than fixed time/frame offsets. A navigation-state head predicts trajectory/goal-reached/unreachable. The checkpoint is trained on 8.7 hours of SCAND demonstrations.

**Evidence in paper.** Closed-loop, five-trial-per-setting results on Spot, ANYmal D, and WAVE ROVER, including held-out environments, detours, warehouse obstacles, chemical-yard routes, and off-road settings. The paper reports that the categorical head completes a detour in 10/10 trials while a matched L1-regression ablation collides in 10/10. The reported inference runs onboard a Jetson AGX Thor (128 GB). The paper evaluates unseen embodiments, but not a G1.

**Limits / interpretation.** Small setting-level trial counts; primary hardware is quadruped, Spot, and a rover. The method is short/medium-horizon waypoint navigation, not global semantic planning or a whole-body G1 controller. “One small dataset” is a useful data-efficiency claim, not evidence of G1 transfer. The robot-specific low-level waypoint controller and odometry remain necessary.

**G1 fit.** Interesting action representation and metric-distance supervision to benchmark against a G1-compatible waypoint model. Do not treat as a drop-in G1 checkpoint.

## 10. Can Vision Foundation Models Navigate? — real-world VNM evaluation

[Can Vision Foundation Models Navigate? Zero-Shot Real-World Evaluation and Lessons Learned (arXiv:2603.25937)](https://arxiv.org/html/2603.25937v2) — **Full paper read**

**What it is.** Real-world comparison of GNM, ViNT, NoMaD, NaviBridger, and CrossFormer on Spot and Clearpath Bunker in corridor, office loop, doorway discrimination, stairs, and snow settings. A reference route/topological map is collected first; the policies then navigate using goal/subgoal images. Bunker lacks built-in collision avoidance; Spot’s controller prevents some collisions.

**Evidence / correction.** In the corridor (three trials), GNM and ViNT each have 0/3 collisions, while NoMaD has 3/3. In the office loop, ViNT has 1/10 collisions, GNM 5/10, NoMaD 2/10, and NaviBridger 9/10. Thus the evidence does **not** support a blanket GNM-over-ViNT ranking. The authors find that models can follow portions of routes but still mis-predict goals or collide; visually repetitive indoor scenes create goal ambiguity. GNM’s simpler visual encoder sometimes compares favorably, but small trial counts and setting-specific outcomes matter.

**Limits / interpretation.** Mobile robots, not humanoids; small real-world trial counts; no social navigation; the study itself says collision avoidance and goal prediction need geometric reasoning and that data composition matters. Collision counts are entangled with platform controllers.

**G1 fit.** Use as evaluation-design guidance and a corrective baseline paper, not as a G1 policy recommendation.

## 11. EgoNav — learned waypoint + geometry-aware local planner

[EgoNav: Bridging Learned Waypoints and Geometry-Aware Local Control for Robust Indoor Navigation (arXiv:2608.25642)](https://arxiv.org/html/2608.25642v1) — **Full paper read, including limitations and appendices**

**What it is.** A hierarchical image-goal navigation system: VPR localizes on an offline topological map, GNM predicts an ego-centric waypoint, semantic RGB-D segmentation samples traversable skeleton candidates, and a multi-term score balances obstacle clearance, global-path coherence, and fidelity to the learned prior. A Falco local planner generates collision-checked paths; its parameters are adjusted using the waypoint correction and clearance.

**Evidence in paper.** In the physical-humanoid evaluation, the robot is mounted on an omnidirectional chassis with an Orbbec Gemini335L RGB-D camera; inference runs on Jetson Orin NX and control on Intel NUC. This is **not** a bipedal G1 evaluation. In the reported real-world episodes, success is 73.3% / 66.7% / 46.7% at short/medium/long distances, versus 60.0% / 50.0% / 33.3% for PlaceNav+Falco. Ten real dynamic-obstacle episodes show lower success than static scenes (50% vs 70% for EgoNav), and avoidance is explicitly reactive rather than predictive. The 10–20 m simulation ablation increases SR from 56.7% for PlaceNav+Falco to 76.7% for full EgoNav; removing directional coherence produces the largest ablation loss.

**Limits / interpretation.** The topological route is pre-collected, camera is forward-facing, and VPR/localization errors accumulate. The paper says open-loop backtracking works only for short detours; learned waypoint generalization is limited by training distribution and detours can leave map coverage. This is a system contribution rather than a new foundation model.

**G1 fit.** Strong architectural pattern for coupling learned waypoints to geometry and a reactive local planner; porting to a biped requires footprint/turning/step feasibility and whole-body control validation.

---

# Other relevant papers/models discovered — screened, not fully read in this pass

These are discovery-screened leads, not full-paper conclusions. I am listing them so that no search-result summary is mistaken for a full audit.

| Paper/model | Why it is worth the next read | Current status |
|---|---|---|
| [X-NavDP (arXiv:2607.28560)](https://arxiv.org/html/2607.28560v1) | RL post-training for NavDP, including G1 and other embodiments; targets detours, recovery, and embodiment transfer. Reported headline improvements are promising, but check all real-trial counts and failure cases. | Abstract/selected sections screened only |
| [X-Nav (arXiv:2611.17598)](https://arxiv.org/html/2611.17598v1) | ~100 m indoor-to-outdoor language mission on Lingxi X2; useful systems/data-engine idea. MELIOR input is RGB-only, but LiDAR/odometry still aid target approach and low-level control. | Abstract/selected sections screened only |
| [GuideWalk (arXiv:2606.10449)](https://arxiv.org/abs/2606.10449) | Unified locomotion/navigation and terrain-adaptive teacher; hardware platform is Kuavo, not G1. | Discovery/abstract screened |
| [NavFoM (ICLR 2026)](https://proceedings.iclr.cc/paper_files/paper/2026/file/ceb45c48e29e7f49b0b47edb98e43691-Paper-Conference.pdf) | Large embodied-navigation model with broad tasks/platforms; reported remote 4090/5090 inference makes it less directly suitable for edge-G1 use. | Discovery/abstract screened |
| [SidewalkBench (arXiv:2606.16953)](https://arxiv.org/html/2606.16953v2) | Large pedestrian-reactive sidewalk test suite; reported pedestrian-crossing tests are exceptionally hard. Useful for social robustness, though simulation and non-humanoid focused. | Discovery/abstract/selected sections screened |
| [PEDS social benchmark](https://pedsral26.github.io/) and [dataset](https://huggingface.co/datasets/arena-rosnav/PEDS37) | Tests how choice of pedestrian simulator/driver changes robot-policy conclusions; modular ROS 2 benchmark. | Discovery/site screened |
| [HumanoidVLN (arXiv:2608.12860)](https://arxiv.org/html/2608.12860v1) | Physics-grounded humanoid VLN benchmark, with a small number of paired real G1 episodes. | Discovery/abstract screened |
| [NavIsaacLab (arXiv:2606.26265)](https://arxiv.org/html/2606.26265v1) | Realistic crowd benchmark; may complement DPed-VLN/SidewalkBench. | Discovery/abstract screened |
| [TAPNAV (arXiv:2610.10748)](https://arxiv.org/abs/2610.10748) | Tactile active perception for G1 navigation; useful when vision is degraded, but not a visual/social baseline. | Discovery/abstract screened |
| [TANGO (arXiv:2609.09158)](https://arxiv.org/html/2609.09158v2), [OpenBelief-Nav (arXiv:2608.13923)](https://arxiv.org/html/2608.13923), [HINT-VLM (arXiv:2611.11665)](https://arxiv.org/html/2611.11665v1), [NavWAM (arXiv:2606.13494)](https://arxiv.org/abs/2606.13494) | Recent world-model, belief/memory, VLM, and action-model lines that could inform a broader model comparison. | Discovery/abstract/selected search snippets only |
| [Whole-body confined-space planning (arXiv:2608.10220)](https://arxiv.org/abs/2608.10220), [semantic-aware locomotion / execution-aware navigation (arXiv:2610.07396)](https://arxiv.org/abs/2610.07396) | Important adjacent categories: whole-body collision/clearance and execution-aware locomotion; do not confuse these with general vision-language navigation models. | Metadata/abstract leads only |

### New synthesis from the discovery set

- Treat **whole-body locomotion**, **local obstacle avoidance**, **global/mapless navigation**, **VLN/task planning**, **social navigation**, and **benchmarks** as separate capability categories. A model may cover more than one, but a benchmark score in one does not establish the others.
- For G1, the strongest papers are the ones that actually execute on a biped (RoM-Nav, FocusNav, the human-data EgoNav, LHNav, Caging VLN). SAFER-Nav, GemNav, VISTA’s main quantitative tests, SidewalkBench, and DPed-VLN are useful adjacent evidence but not equivalent G1 proof.
- Reported collision-free claims need sensor/map/assumption context. Caging’s proof is about its modeled planar footprint and observed SDF. RoM-Nav’s shield is planar and LiDAR-based. FocusNav’s gains trade off stability against aggressive avoidance. EgoNav’s glass advantage comes from appearance features but its deployment was not compared head-to-head with another policy.
- Social safety requires more than “no collision”: assess personal-space duration, near misses, speed/yield behavior, crowd density, falls, and pedestrian-driver sensitivity. PEDS and DPed-VLN suggest that simulator/driver choice changes results materially.

# Reading audit / what remains

The following 11 primary papers were fully read in this pass: RoM-Nav; FocusNav; human-data EgoNav; SAFER-Nav; VISTA; LHNav; Caging VLN; DPed-VLN; GemNav; Can Vision Foundation Models Navigate?; and geometry-aware EgoNav. Full-paper status means the complete available HTML paper, results, limitations, and appendices were reviewed where the HTML exposed them. It does not mean that every cited reference inside those papers was also read.

The additional leads in the table remain screened only. To honor the “read every paper” requirement for the complete discovery list, the next pass should systematically read X-NavDP, X-Nav, GuideWalk, NavFoM, SidewalkBench, PEDS, HumanoidVLN, NavIsaacLab, and then the TANGO/OpenBelief-Nav/HINT-VLM/NavWAM group. Claims from those papers should remain marked provisional until that pass is complete.
