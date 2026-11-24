# 3D scene representation and perception for G1 navigation

Status: engineering review and architecture decision record  
Last reviewed: 2026-07-17  
Applies to: Unitree G1 EDU, 43-DoF project configuration with MID-360 LiDAR, D435i RGB-D, IMU, joint encoders, onboard control, and tethered offboard compute

## Decision

Use a hybrid map stack. No single representation is good enough for localization, collision avoidance, visual reconstruction, semantics, and long-horizon planning at the same time.

| Responsibility | Recommended representation | Reason |
| --- | --- | --- |
| State estimation | FAST-LIO2 LiDAR-inertial odometry, fused with proprioception | Metric, low latency, and independent of scene texture |
| Immediate collision safety | Local 3D occupancy plus ESDF, derived from current LiDAR and RGB-D observations | Explicit free, occupied, unknown, and clearance queries |
| Predictive planning | 4D sparse voxel memory with uncertainty and tracked dynamics | Keeps geometry, time, and learned features in one local structure |
| Global visual and semantic context | Semantic 3D Gaussian Splatting map, maintained offboard | Fast rendering, object grounding, relocalization support, and digital-twin use |
| Long-horizon reasoning | Object and place scene graph linked to the metric map | Compact symbolic relationships for task planning |
| Fail-safe control | Proprioceptive and inertial CBF, watchdog, and trajectory buffer | Remains available if cameras, LiDAR, or the tether fail |

The local metric map is the authority for collision avoidance. A NeRF or Gaussian map may propose goals, provide semantics, or improve localization, but it must not clear an obstacle or certify a trajectory by itself.

## 1. Scope and evaluation criteria

This review covers four questions:

1. What do 3D Gaussian Splatting and NeRF contribute to robot navigation?
2. How should stereo, LiDAR, and monocular depth be used and fused?
3. How do online SLAM and offline photogrammetry differ?
4. Which other 3D representations belong in a navigation stack?

The comparison uses navigation criteria rather than rendering quality alone:

- metric accuracy and scale observability;
- free-space and clearance queries;
- update latency and worst-case behavior;
- robustness to lighting, texture, motion, glass, and occlusion;
- support for dynamic objects and stale-data detection;
- memory, bandwidth, and compute cost;
- relocalization and loop closure;
- semantic and language grounding;
- behavior after a sensor or network failure.

## 2. Gaussian splatting and NeRF for navigation

### 2.1 What 3D Gaussian Splatting represents

3D Gaussian Splatting, or 3DGS, represents a scene as anisotropic Gaussian primitives. Each primitive has a 3D position, covariance, opacity, and view-dependent appearance coefficients. The original method combines adaptive density control with a visibility-aware rasterizer and reports real-time novel-view rendering at 1080p on its evaluation scenes [1]. That is a rendering result, not a guarantee about mapping rate, pose accuracy, or planning latency on a robot.

3DGS is useful in robotics because the representation is explicit enough to inspect, render, attach features to, and update selectively. It works well for:

- photorealistic digital twins and operator views;
- image-based relocalization against a known scene;
- semantic feature attachment to splats or object clusters;
- viewpoint selection and active reconstruction;
- generating visual observations for simulation and policy testing.

The important limitation is geometric meaning. Opacity is learned for image formation. It does not automatically mean solid matter, free space, or traversability. Thin geometry can be incomplete, transparent objects can be wrong, and moving objects can leave stale or duplicated splats. Collision checking therefore needs a conservative geometric conversion or a separate map.

[Splat-Nav](https://arxiv.org/abs/2403.02751) illustrates the extra machinery required. Its planner constructs a safe polytope corridor from explicit collision constraints, while its localization module estimates pose from RGB. The paper reports about 25 Hz pose estimation and replanning above 2 Hz [2]. The safety property comes from Splat-Plan, not from ordinary alpha-composited rendering.

### 2.2 What NeRF represents

A Neural Radiance Field, or NeRF, learns a continuous function from 3D position and viewing direction to volume density and emitted radiance. The original NeRF optimizes one scene from posed images and synthesizes new views with differentiable volume rendering [3]. Its reported capability is novel-view synthesis within the captured scene. It should not be described as generalization to arbitrary unseen environments.

NeRF has several attractive properties:

- continuous spatial queries without a fixed voxel resolution;
- compact learned features for appearance and, in some variants, semantics;
- differentiable rendering for pose refinement;
- smooth reconstruction in regions supported by enough views.

Classic NeRF also has poor defaults for navigation. Per-scene optimization and ray marching are expensive, density does not equal certified occupancy, geometry can be view dependent, and the original formulation assumes a static scene. Faster encodings reduce training and rendering time, but they do not remove the need for uncertainty, dynamics handling, or a safety map.

Neural SLAM systems often become hybrids for this reason. [ESLAM](https://arxiv.org/abs/2211.11704), for example, uses multi-scale feature planes and shallow decoders to produce TSDF and RGB values. Its paper reports more than 50 percent improvement on its selected reconstruction and localization comparisons and up to a 10-fold speedup over the dense baselines tested [4]. Those are benchmark-relative results, not a general claim that NeRF replaces geometric SLAM.

### 2.3 Practical comparison

| Property | 3DGS | NeRF and neural implicit fields | Navigation consequence |
| --- | --- | --- | --- |
| Rendering | Rasterized splats, usually fast after reconstruction | Sampled field and volume rendering, usually more expensive | 3DGS is better suited to frequent visual queries |
| Geometry | Explicit primitive centers and covariances, but learned opacity | Continuous density or SDF, depending on the method | Neither density nor opacity is automatically collision-safe |
| Online update | Local primitive insertion, pruning, and optimization are possible | Incremental optimization is possible but can be costly | Both need bounded update work and stale-map detection |
| Dynamics | Static by default | Static by default | Moving people need tracking or static-dynamic separation |
| Semantics | Features can be attached per splat or cluster | Features can be decoded from the field | Useful for goal selection, not as the final safety check |
| Memory | Can become large as primitive count grows | Network and feature-grid size can be compact | Measure scene growth and VRAM, not only model size |
| Failure mode | Floaters, holes, duplicated moving objects, appearance leakage | Density ambiguity, slow queries, pose and scale coupling | Fall back to fresh metric sensors when confidence drops |

For this G1 design, 3DGS is preferable to NeRF for the global visual-semantic layer. NeRF-style SDF decoders remain relevant as a research option for compact reconstruction, but neither representation should sit in the 500 Hz safety path.

## 3. Stereo, LiDAR, and monocular depth

### 3.1 LiDAR

LiDAR directly measures range from emitted light. It provides metric observations without depending on visible texture and works in darkness. Accuracy, field of view, angular resolution, and range depend on the specific device. A solid-state LiDAR is not inherently 360 degrees, and a robotics LiDAR should not be described as universally millimeter accurate.

Typical failure cases include low-return dark materials, glass, multi-path reflections, near-field blind zones, rain or fog, and motion distortion. IMU synchronization and calibration matter because a walking humanoid rotates and translates the sensor during each scan.

LiDAR is the primary metric sensor in this architecture because its failures differ from those of the camera and because [FAST-LIO2](https://arxiv.org/abs/2107.06829) supports both spinning and solid-state scan patterns. The paper reports direct raw-point registration and up to 100 Hz odometry and mapping in its tested environments [5]. The deployed rate must still be measured on the actual MID-360, compute module, and map size.

### 3.2 Stereo and RGB-D

Rectified stereo estimates depth from disparity:

\[
z = \frac{fB}{d}
\]

where \(z\) is depth, \(f\) is focal length in pixels, \(B\) is the calibrated baseline, and \(d\) is disparity. A first-order uncertainty approximation is:

\[
\sigma_z \approx \frac{z^2}{fB}\sigma_d
\]

The quadratic term explains why stereo depth becomes uncertain at long range. Passive stereo also degrades on textureless walls, repeated patterns, specular surfaces, occlusion boundaries, and low light. Active stereo improves some indoor scenes but can fail in sunlight or when several projectors interfere.

The D435i is valuable for dense near-field geometry, edge detail, and visual semantics. It should supplement the LiDAR rather than silently overwrite it. Calibration, hardware timestamps, depth validity masks, and frame transforms must be checked continuously.

### 3.3 Monocular depth

Monocular depth models infer geometry from learned image cues. Relative-depth models recover ordering but not reliable metric scale. Metric variants learn a scale prior, yet their absolute error changes with camera intrinsics, scene type, range, and domain shift.

[Depth Anything V2](https://arxiv.org/abs/2406.09414) provides relative and metric model variants and improves detail and efficiency over its predecessor [6]. A 2025 indoor robotics evaluation found mean errors between 0.32 m and 0.66 m across six datasets. For targets within 2 m, 89.1 percent of errors fell within plus or minus 0.5 m. The same study concludes that the evaluated model had significantly lower metric accuracy than LiDAR and was not suitable for high-precision indoor navigation or obstacle avoidance [7]. The 89.1 percent figure therefore argues against treating it as a LiDAR replacement.

Good uses for monocular depth in this stack include:

- filling semantic context outside the dense RGB-D range;
- proposing depth where active sensors have no return;
- generating weak labels for representation learning;
- ranking surfaces or objects by approximate distance;
- detecting disagreement that triggers a slower or safer mode.

It must not be the only source used to clear free space near the robot.

### 3.4 Fusion policy

Fusion should preserve provenance and uncertainty instead of averaging every depth source into one map.

1. Deskew and register LiDAR using the IMU and current state estimate.
2. Reproject RGB-D observations with their confidence and validity masks.
3. Reject measurements that violate calibration, timestamp, range, or innovation gates.
4. Update occupancy and surface estimates with sensor-specific inverse models.
5. Use monocular depth as a soft prior or learned feature, not as hard free-space evidence.
6. Track source age. A plausible but stale map is unsafe.

## 4. SLAM and photogrammetry

SLAM and photogrammetry share bundle adjustment, correspondence, and multi-view geometry, but their operating goals differ.

### 4.1 Online SLAM

A practical SLAM system has two connected parts:

- The front end synchronizes sensors, estimates frame-to-frame motion, rejects outliers, and creates local constraints.
- The back end optimizes a pose graph or factor graph, detects loop closures, and manages global consistency.

Odometry alone produces a locally smooth trajectory but accumulates drift. SLAM adds map reuse and loop closure. A complete comparison should report both local motion error and global trajectory consistency.

Representative choices are:

- LiDAR-inertial SLAM for metric state estimation in weakly textured or dark areas. FAST-LIO2 is the selected baseline here [5].
- Visual-inertial SLAM when cameras and IMU provide good overlap. [ORB-SLAM3](https://arxiv.org/abs/2007.11898) supports monocular, stereo, RGB-D, and visual-inertial modes with multi-map relocalization [8].
- Dense learned visual SLAM as an experimental reconstruction path. [MASt3R-SLAM](https://arxiv.org/abs/2412.12392) reports dense monocular SLAM at 15 FPS with loop closure and global optimization [9]. This is evidence for real-time dense reconstruction, not proof of photogrammetry-level accuracy on every scene.

### 4.2 Offline photogrammetry

Photogrammetry usually runs Structure from Motion followed by Multi-View Stereo. It can optimize all images jointly, re-run matching, reject weak views, and spend much more compute on surface reconstruction and texture generation. This makes it a good tool for building a reference model of the lab.

It is not a navigation state estimator. It assumes sufficient overlap, parallax, calibration quality, and mostly static appearance. Textureless walls, reflective surfaces, moving people, auto-exposure changes, and repeated structure can all damage the result.

For this project, photogrammetry or an offline 3DGS reconstruction should provide a surveyed global reference and digital twin. Online FAST-LIO2 and the local safety map should continue to operate even if the reference model is unavailable.

### 4.3 Evaluation measures

Do not compare systems using one context-free centimeter figure. Report:

- Absolute Trajectory Error for global pose accuracy;
- Relative Pose Error or drift per meter for local motion;
- loop-closure precision, recall, and recovery time;
- surface accuracy and completeness against a surveyed reference;
- map update latency and pose latency at p50, p95, and p99;
- tracking failure rate and time to relocalize;
- CPU, GPU, VRAM, memory growth, power, and network load.

The dataset, trajectory length, sensor configuration, and alignment method belong next to every number.

## 5. Alternative 3D scene representations

| Representation | What it stores | Best role | Main limitation |
| --- | --- | --- | --- |
| Probabilistic occupancy grid or octree | Free, occupied, and unknown space | Collision checking, exploration, conservative mapping | Resolution-memory trade-off and blocky surfaces |
| TSDF | Truncated signed distance near observed surfaces | Denoising, surface fusion, mesh extraction | Not a complete Euclidean clearance field |
| ESDF | Euclidean distance to the nearest obstacle over mapped free space | Trajectory optimization and clearance constraints | Costs more to maintain and inherits upstream map errors |
| Point cloud or surfel map | Samples of observed surfaces, sometimes with normals | Fast registration and incremental mapping | Free space and watertight surfaces are implicit |
| Mesh | Vertices, faces, and explicit surface topology | Simulation, visualization, contact queries | Incremental topology repair is difficult |
| 3DGS | Appearance-bearing Gaussian primitives | Visual reference, semantics, relocalization, digital twins | Opacity is not certified occupancy |
| NeRF or neural SDF | Continuous learned field | Compact reconstruction, differentiable queries | Optimization cost, uncertainty, and difficult safety certification |
| Sparse learned voxel grid | Geometry, features, and time in active cells | Predictive local memory and learned planning | Requires task-specific training and bounded memory management |
| Object or place graph | Objects, rooms, actions, and relationships | Task planning, language grounding, long-term memory | Too abstract for metric collision checks |
| Topological graph | Places and traversable connections | Large-scale route planning | Needs a metric local planner at each place and edge |

TSDF and ESDF are related but not interchangeable. A TSDF estimates distance to a measured surface only within a truncation band and is suited to fusion and meshing. An ESDF stores Euclidean obstacle distance through the planning volume. [Voxblox](https://arxiv.org/abs/1611.03631) incrementally constructs an ESDF from a TSDF for onboard trajectory optimization [10].

[OctoMap](https://octomap.github.io/) remains a useful reference for probabilistic 3D occupancy because it explicitly models free, occupied, and unknown space in an octree [11]. For a humanoid, preserve the 3D map around the body even if a 2D planner is used for base routing. Nav2's voxel layer keeps a 3D environmental model but collapses it to 2D for planning and control [12]. That behavior is not enough for arm, torso, overhang, and tether clearance without an additional 3D check.

## 6. Recommended G1 architecture

### 6.1 Reactive onboard loop

Design target: 200 to 500 Hz for control and safety checks, with sensor estimators updating at their measured rates.

Inputs:

- MID-360 LiDAR;
- D435i RGB and depth;
- IMU;
- 43 joint positions and velocities;
- foot contact, motor, and tether state where available.

Onboard functions:

- FAST-LIO2 metric odometry;
- rolling occupancy plus ESDF around the full robot body;
- proprioceptive and inertial CBF constraints;
- command freshness watchdog;
- trajectory buffer and controlled safe-stand policy;
- whole-body control for the configured 43-DoF G1 EDU.

The official G1 specification lists 23 joints for the base model and 23 to 43 for G1 EDU, depending on options [13]. This repository's `config/g1_kinematics.yaml` selects the 43-DoF EDU configuration with Dex3-1 hands. Architecture diagrams and action interfaces must use that project configuration, not the base 23-joint figure.

### 6.2 Predictive offboard loop

Design target: 5 to 40 Hz, subject to measured end-to-end latency.

- Fuse metric geometry and features into a 4D sparse voxel memory.
- Predict short-horizon scene and robot outcomes with the JEPA and WorldRFT stack.
- Sample tether-aware trajectories with MPPI.
- Penalize body collision, tether wrap, stale observations, uncertainty, and loss of local-map support.
- Send timestamped, bounded-horizon trajectory segments rather than raw actuator commands.

Every command needs a generation timestamp, validity horizon, source state ID, map version, and uncertainty. The onboard layer rejects stale or dynamically infeasible segments.

### 6.3 Semantic offboard loop

Design target: 0.5 to 1 Hz for global scene updates and task grounding.

- Maintain a semantic 3DGS digital twin of the mostly static environment.
- Attach DINO, Slot Attention, and VL-JEPA features to objects or spatial clusters.
- Link objects and places to the metric frame and scene graph.
- Propose task goals, search targets, and relocalization hypotheses.

The semantic loop may add cost or mark an area unknown. It cannot clear locally observed occupancy.

### 6.4 ROS 2 and Nav2 boundary

If Nav2 is used, publish a conservative 2D projection for global base routing and keep a separate 3D local collision checker for the humanoid body and tether. The projection must preserve overhang risk, unknown space policy, and the current robot footprint. A custom costmap layer can ingest vetted geometry from the global representation, but live LiDAR and RGB-D observations remain dominant.

## 7. Failure policy

| Failure | Required behavior | Capability that remains |
| --- | --- | --- |
| Offboard process or tether link lost | Reject expired commands, finish only the safe buffer prefix, then controlled safe stand | Onboard CBF, proprioception, IMU, local estimator if sensors remain connected |
| RGB or RGB-D lost | Disable visual semantics and depth fusion, keep LiDAR-inertial navigation at reduced speed | FAST-LIO2 and LiDAR occupancy |
| LiDAR lost | Stop autonomous walking unless a separately validated RGB-D safety mode is active | Balance, CBF, and controlled stand |
| IMU or joint state invalid | Immediate controlled stop because balance state is untrusted | Hardware emergency behavior only |
| Neural map stale or inconsistent | Remove it from planning authority and continue on the local metric map | Local navigation with reduced global capability |
| Local map stale | Reject motion commands and stop | Balance and safe stand |
| Tether state uncertain | Reduce yaw and translation envelope; stop if wrap or tension cannot be bounded | Onboard control inside the safe envelope |

An explicit degraded state is better than a green "nominal" indicator with missing inputs. Status must propagate through dependencies.

## 8. Validation plan

### 8.1 Bench tests

- Verify time synchronization and extrinsics with repeatable residual plots.
- Measure depth error by range, material, lighting, and incidence angle.
- Test glass, dark fabric, polished metal, thin chair legs, stairs, and overhangs.
- Measure map age, estimator latency, and command age at p50, p95, and p99.
- Confirm that monocular predictions cannot clear occupied or unknown cells.

### 8.2 Navigation tests

- Compare LiDAR only, RGB-D only, fused metric, and fused plus neural context.
- Report collisions, minimum clearance, falls, near falls, success rate, path length, and completion time.
- Separate static-map performance from runs with people and moved furniture.
- Test relocalization after occlusion, fast head motion, darkness, and scene change.
- Record every safety intervention and whether it was necessary.

### 8.3 Fault-injection tests

- Drop RGB, depth, LiDAR, IMU, and joint-state messages independently.
- Add timestamp delay, packet reordering, bandwidth limits, and full link loss.
- Freeze the neural map while live obstacles move.
- Inject incorrect scale and pose into the monocular and 3DGS branches.
- Verify deterministic transition to the documented degraded or stop state.

### 8.4 Release gates

A representation enters the safety path only after it demonstrates bounded query time, explicit unknown-space handling, stale-data rejection, calibrated uncertainty, and a tested fallback. Rendering quality metrics such as PSNR or SSIM are useful for the digital twin but do not count as navigation safety evidence.

## 9. Implementation order

1. Bring up calibrated MID-360, D435i, IMU, and 43-DoF state streams with timestamp diagnostics.
2. Validate FAST-LIO2 and a rolling 3D occupancy map.
3. Add ESDF clearance queries and connect them to CBF and trajectory validation.
4. Implement watchdog, trajectory buffer, and safe-stand fault injection.
5. Add the offboard 4D voxel memory and tether-aware MPPI behind the onboard safety gate.
6. Build the offline 3DGS reference, then add semantic features and scene-graph links.
7. Evaluate neural relocalization and planning benefits against the metric-only baseline.
8. Promote only the parts that improve navigation metrics without weakening failure behavior.

## 10. Conclusion

3DGS is the best fit for this project's global visual-semantic representation because it renders quickly and supports editable, feature-bearing primitives. NeRF and neural SDF methods remain useful for compact continuous reconstruction research. Neither is a substitute for fresh metric sensing and explicit free-space reasoning.

The recommended stack is deliberately redundant: LiDAR-inertial SLAM estimates motion, occupancy and ESDF represent local safety, a sparse 4D voxel map supports prediction, 3DGS supplies global visual-semantic context, and a scene graph supports task reasoning. The CBF, watchdog, and trajectory buffer remain onboard so the robot can reach a controlled safe state without the neural stack or tether.

## References

1. Kerbl et al., [3D Gaussian Splatting for Real-Time Radiance Field Rendering](https://arxiv.org/abs/2308.04079), ACM Transactions on Graphics, 2023.
2. Chen et al., [Splat-Nav: Safe Real-Time Robot Navigation in Gaussian Splatting Maps](https://arxiv.org/abs/2403.02751), 2024, revised 2025.
3. Mildenhall et al., [NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis](https://arxiv.org/abs/2003.08934), ECCV, 2020.
4. Johari et al., [ESLAM: Efficient Dense SLAM System Based on Hybrid Representation of Signed Distance Fields](https://arxiv.org/abs/2211.11704), CVPR, 2023.
5. Xu et al., [FAST-LIO2: Fast Direct LiDAR-inertial Odometry](https://arxiv.org/abs/2107.06829), 2021.
6. Yang et al., [Depth Anything V2](https://arxiv.org/abs/2406.09414), NeurIPS, 2024.
7. Louw, Verster, and Dickens, [Assessing Depth Anything V2 monocular depth estimation as a LiDAR alternative in robotics](https://doi.org/10.1051/matecconf/202541704002), MATEC Web of Conferences, 2025.
8. Campos et al., [ORB-SLAM3: An Accurate Open-Source Library for Visual, Visual-Inertial and Multi-Map SLAM](https://arxiv.org/abs/2007.11898), IEEE Transactions on Robotics, 2021.
9. Murai, Dexheimer, and Davison, [MASt3R-SLAM: Real-Time Dense SLAM with 3D Reconstruction Priors](https://arxiv.org/abs/2412.12392), CVPR, 2025.
10. Oleynikova et al., [Voxblox: Incremental 3D Euclidean Signed Distance Fields for On-Board MAV Planning](https://arxiv.org/abs/1611.03631), IROS, 2017.
11. Hornung et al., [OctoMap: An Efficient Probabilistic 3D Mapping Framework Based on Octrees](https://octomap.github.io/), Autonomous Robots, 2013.
12. Open Navigation LLC, [Nav2 voxel layer parameters](https://docs.nav2.org/configuration/packages/costmap-plugins/voxel.html), accessed 2026-07-17.
13. Unitree Robotics, [G1 specifications](https://www.unitree.com/g1/), accessed 2026-07-17.
