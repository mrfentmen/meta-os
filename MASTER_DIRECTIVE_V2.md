# MASTER PROJECT DIRECTIVE: META SENTINEL, META EMBER, AND META SANITAS

(From Del, 2026-10-28. Updated directive — expands and supersedes the Sentinel-only brief of the same morning.)

## 1. PROJECT OVERVIEW

We are developing three related AI-powered public-sector software products for the Meta Global AI Developer Hackathon 2026.

Competition: Meta Global AI Developer Hackathon
Track: Indie — Push the Frontier
Deadline: November 4, 2026, at 9:00 PM Eastern
Available development team: Four AI coding agents

The three products are:

1. Meta Sentinel — NYPD-oriented visual incident awareness and analysis.
2. Meta Ember — FDNY-oriented fire, smoke, and emergency-scene awareness.
3. Meta Sanitas — Department of Sanitation-oriented environmental observation, sanitation inspection, and operational support.

These are distinct applications designed for different departments. They should share an underlying technical foundation wherever practical, while maintaining separate interfaces, workflows, capabilities, and product identities.

The long-term vision is a family of specialized AI tools for public-sector departments, not a generic chatbot with different labels.

We want to demonstrate how multimodal AI can help people interpret visual information, extract relevant observations, organize evidence, identify potential issues, and make better-informed decisions.

We are NOT building a complete municipal operating system in one week. We are building a functional foundation that can support multiple specialized applications.

## 2. CURRENT PROJECT STATUS

Assume all three applications are greenfield projects unless repository inspection proves otherwise.

Do not assume that any functionality has already been implemented.

Before making changes:

* Inspect the current repository.
* Identify the framework, dependencies, existing code, and deployment setup.
* Identify any existing integrations with Meta AI products.
* Check available API credentials and environment configuration without exposing secrets.
* Determine which components can be reused.
* Identify any technical blockers.

Do not overwrite existing work or redesign an existing component without understanding its purpose.

If the repository is empty, establish a clean architecture suitable for rapid development and reliable integration.

## 3. PRODUCT ONE: META SENTINEL

### Purpose

Meta Sentinel is the NYPD-oriented application.

Its primary purpose is to investigate whether multimodal AI can analyze visual input, identify observable actions or potentially significant events, and present evidence-supported assessments for human review.

The initial prototype should use a phone's front-facing camera or a webcam.

The developer will perform staged actions in front of the camera to test whether the system can correctly describe what is happening.

We do not need access to actual police CCTV systems to demonstrate this capability.

### Initial scenarios

Implement a scenario-driven evaluation system covering:

1. Normal walking and standing.
2. Dancing and energetic movement.
3. Waving arms or making ambiguous gestures.
4. A staged argument.
5. A staged physical altercation.
6. A person falling or deliberately lowering themselves.
7. Actions that resemble aggression but are harmless.
8. Situations where the camera angle, lighting, or partial obstruction makes interpretation difficult.

The exact test suite should be adjusted to what can be implemented and measured reliably.

### Required capabilities

A. Live visual input

* Request camera permission.
* Display the active camera feed.
* Start and stop analysis.
* Handle camera errors.
* Clearly indicate when analysis is active.
* Allow the user to reset a session.

B. Event observation

The application should attempt to identify observable actions, movement, and relevant changes in the scene.

For example, the model may describe rapid arm movements, two people making physical contact, a person falling, or ordinary dancing.

It must distinguish observations from conclusions.

C. Event assessment

For each potential event, produce a structured result containing:

* Timestamp.
* Observable action.
* Event category.
* Relevant visual evidence.
* Confidence information, if supported.
* Uncertainty and alternative explanations.
* Whether human review is recommended.

D. Review interface

Display the event assessment in a clear interface, with an event history and the ability to inspect previous assessments.

E. Evaluation

Measure false positives, false negatives, precision, recall, and processing latency where the test design permits.

Include harmless actions that resemble suspicious activity so that the evaluation does not reward the system simply for flagging everything.

### Important limitations

Meta Sentinel is a prototype for visual incident awareness. It does not establish that a crime has occurred, determine guilt, or reliably infer criminal intent from body movements.

Do not implement face recognition, identity tracking across unrelated footage, or automatic police dispatch as part of the initial prototype.

Use staged scenarios and consenting participants. Do not connect to public CCTV feeds unless a separate, authorized integration is explicitly approved.

The demo should establish what the system can and cannot determine from visual evidence.

## 4. PRODUCT TWO: META EMBER

### Purpose

Meta Ember is the FDNY-oriented application.

Its purpose is to investigate how visual AI can help identify visible indicators of fire-related hazards and communicate potentially important observations to a human reviewer.

The initial prototype should use prerecorded, appropriately sourced test footage or controlled, safe visual demonstrations.

Do not create an actual fire to test the system.

### Initial scenarios

Test examples of:

1. Visible smoke.
2. Visible flames.
3. Normal scenes without fire or smoke.
4. Steam or fog that might be mistaken for smoke.
5. Lighting conditions that resemble flames.
6. Partially obscured or distant visual hazards.
7. Scenes where the model cannot confidently determine what is happening.

### Required capabilities

A. Visual analysis

Analyze supported image or video inputs and identify potential visible indicators of fire, smoke, or related hazards.

B. Structured assessment

Return:

* Timestamp or frame reference.
* Observed visual condition.
* Potential hazard category.
* Relevant visual evidence.
* Uncertainty.
* Recommended human review status.

C. Evidence review

Display the relevant input frame and the corresponding assessment so a reviewer can understand why the system raised an alert.

D. Evaluation

Measure performance against labeled positive and negative test examples. Specifically investigate confusion between smoke and visually similar phenomena.

### Important limitations

Meta Ember is not a certified fire-detection system and must not be presented as a replacement for fire alarms, established detection systems, or professional emergency judgment.

Do not automatically dispatch emergency services based on an unverified model output.

Clearly disclose the tested conditions and limitations.

## 5. PRODUCT THREE: META SANITAS

### Purpose

Meta Sanitas is the Department of Sanitation-oriented application.

Its purpose is to investigate how visual AI can assist with sanitation observations and environmental maintenance workflows.

Potential uses include identifying visible waste accumulation, overflowing public trash bins, illegal dumping indicators, blocked sidewalks, and other visible sanitation concerns.

These are candidate features, not claims that every feature must be completed for the hackathon.

### Initial scenarios

Test examples of:

1. An overflowing trash bin.
2. Waste accumulated on a sidewalk.
3. A visibly obstructed pedestrian path.
4. A relatively clean sidewalk.
5. A normal collection area.
6. Objects that resemble discarded waste but are not clearly refuse.
7. Images with poor visibility or ambiguous conditions.

### Required capabilities

A. Visual inspection

Analyze an image or supported video input and identify potential sanitation issues.

B. Structured observations

Return:

* Observed condition.
* Potential issue category.
* Visual evidence.
* Severity assessment, if a defensible rubric exists.
* Uncertainty.
* Recommended inspection or review status.

C. Inspection history

Allow the user to review previous assessments during a session.

If location or mapping is added, use only explicitly provided or appropriately authorized location information. Do not invent geographic coordinates.

D. Evaluation

Compare predictions against labeled test examples and measure false alarms and missed issues.

### Important limitations

The model should not claim that a sanitation violation has legally occurred based on an image alone.

Distinguish visible conditions from legal determinations, property ownership, intent, and responsibility.

Do not automatically issue citations or penalties.

## 6. SHARED TECHNICAL FOUNDATION

All three products should share common infrastructure where doing so reduces development time and improves reliability.

Potential shared components include:

* Camera and image input utilities.
* Video-frame sampling where supported.
* Model adapters.
* Structured output validation.
* Timestamp handling.
* Event and assessment schemas.
* Confidence and uncertainty presentation.
* Error handling.
* Evaluation tooling.
* Logging and diagnostics.
* Common interface components.
* Configuration management.
* Test utilities.

Each application should have its own product configuration defining:

* Product name.
* Target department.
* Available analysis modes.
* Relevant event categories.
* Output labels.
* Review workflow.
* Evaluation scenarios.
* Applicable limitations.

Do not create three entirely separate codebases if a shared foundation is practical.

Equally, do not create an elaborate framework that delays delivery. The architecture must make the three products easier to build, not harder.

A shared model adapter may support different workflows, but it must not pretend that all three departments have identical needs.

## 7. META AI INTEGRATIONS

Investigate the relevant Meta AI technologies and determine their actual capabilities.

### Muse Spark

Investigate its supported multimodal input, reasoning, and structured-output capabilities.

Determine:

* Whether image input is supported by the available interface.
* Whether video can be submitted directly or must be processed into frames.
* What API access is available.
* What authentication and rate limits apply.
* Whether the model can return validated structured assessments.

### SAM 3.1

Investigate its supported visual segmentation and object-identification capabilities.

Determine whether segmentation or object identification would materially improve the detection pipeline.

Do not assume that SAM alone performs temporal reasoning, recognizes criminal intent, or provides a complete incident-classification system.

### Muse Image / Wonder

Determine whether image-generation or editing capabilities provide a meaningful benefit.

Do not add image generation merely to increase the number of Meta products mentioned in the submission.

### Integration requirements

Verify current documentation, API access, model names, SDKs, and hackathon eligibility.

Do not invent endpoints or APIs.

Do not create mock integrations and describe them as working Meta AI integrations.

If a capability is unavailable, document the limitation and recommend a feasible alternative consistent with the hackathon rules.

Each integrated technology must have a defined technical role.

## 8. FOUR-AGENT WORK ALLOCATION

Coordinate four agents with clear ownership and minimal overlap.

### Agent 1: Shared frontend and interaction

Own:

* Camera interface.
* Image and video input.
* Shared UI components.
* Product selection and navigation.
* Event history.
* Results display.
* Loading and error states.
* Responsive design.

Deliver working components and a documented interface contract.

### Agent 2: Meta AI integration

Own:

* API and SDK verification.
* Model access.
* Input preparation.
* Model adapters.
* Structured model responses.
* Error handling.
* Server-side credential handling.
* Integration documentation.

Verify the actual model behavior before reporting completion.

### Agent 3: Product logic and evaluation

Own:

* Sentinel event categories and test cases.
* Ember smoke and fire test cases.
* Sanitas sanitation test cases.
* Ground-truth labels.
* Evaluation scripts.
* Performance metrics.
* False-positive and false-negative analysis.
* Baseline comparisons where feasible.

Create reusable evaluation infrastructure while preserving separate test suites for each product.

### Agent 4: Integration, testing, and demonstration

Own:

* Shared architecture.
* Interface compatibility.
* Integration.
* End-to-end tests.
* Build and runtime verification.
* Critical-path debugging.
* Demo reliability.
* Submission preparation.

This agent must test actual functionality rather than rely on other agents' completion reports.

### Coordination rules

Before parallel development:

1. Define the shared data contracts.
2. Define module ownership.
3. Establish the project structure.
4. Communicate integration requirements.
5. Identify shared files that must not be modified independently.

Agents must not silently change interfaces, duplicate major components, or overwrite other agents' work.

All work must be committed or otherwise integrated through a process appropriate to the repository.

## 9. INITIAL DATA CONTRACT

Use a common assessment format where practical.

A proposed structure is:

{
"product": "sentinel | ember | sanitas",
"timestamp": "ISO-8601 timestamp",
"observations": [
{
"category": "observation category",
"description": "what is visibly present",
"evidence": "supporting visual details",
"confidence": null
}
],
"assessment": {
"category": "potential event category",
"summary": "concise interpretation",
"uncertainty": [
"unresolved ambiguity"
],
"requires_human_review": true
},
"processing": {
"model": "actual model identifier",
"latency_ms": null
}
}

This is a proposed contract. Adapt it to the selected implementation and the real capabilities of the model.

Never fabricate confidence scores, latency measurements, model identifiers, or evidence references.

Validate model responses before displaying them. If a response is invalid, handle the error explicitly.

## 10. TESTING AND QUALITY REQUIREMENTS

The applications must execute real analysis.

Do not substitute static example results for live model outputs in the critical workflow.

Every critical feature should have an acceptance criterion.

For each product, verify:

* Input works.
* The actual processing pipeline executes.
* A structured assessment is returned.
* The interface displays the assessment correctly.
* Errors are handled.
* The system does not claim unsupported capabilities.
* Test results are reproducible.

Run unit, integration, and end-to-end tests where appropriate.

Measure model latency and performance under the conditions actually tested.

Document test sample sizes and limitations.

If a feature cannot be completed, identify it clearly instead of leaving a fake implementation behind.

## 11. PRODUCT DESIGN

The three products should look like members of the same product family, but each should have a clear identity.

Use a clean, restrained, operational interface.

Prioritize:

* Readability.
* Clear status indicators.
* Useful timestamps.
* Evidence visibility.
* Uncertainty disclosure.
* Functional controls.
* Error transparency.
* Fast access to previous assessments.

Avoid:

* Decorative complexity.
* Fake real-time status.
* Hardcoded activity feeds presented as live data.
* Unnecessary gradients and visual clutter.
* Buttons that do nothing.
* Artificial confidence indicators.
* Excessive configuration that does not improve the workflow.

Do not spend time polishing visual details while the critical path is broken.

## 12. DEMONSTRATION STRATEGY

The three products should share a technical foundation, but the demonstration must show distinct use cases.

### Meta Sentinel demonstration

Use the developer's phone camera or webcam.

Perform normal and staged actions. Show what the model observes, what it flags, what it cannot determine, and how its output compares with the expected scenario.

### Meta Ember demonstration

Use safe, prerecorded footage or labeled images representing smoke, flames, and visually similar harmless conditions.

Show whether the system distinguishes them and how it handles ambiguity.

### Meta Sanitas demonstration

Use representative images of overflowing bins, visible waste, blocked paths, and clean environments.

Show the resulting inspection assessments and the evaluation results.

Only demonstrate features that actually work.

Prepare prerecorded backup inputs in case live camera permissions, network access, or model availability fail.

Do not present prerecorded model results as live analysis.

## 13. EXECUTION PLAN

We have until November 4, 2026, at 9:00 PM Eastern.

Move quickly and prioritize working software.

Phase 1: Inspect and establish

* Inspect the repository.
* Verify Meta AI access.
* Define architecture and data contracts.
* Allocate agent ownership.
* Identify critical blockers.

Phase 2: Prove the shared critical path

Build one working flow:

Visual input → Actual model processing → Validated structured assessment → Displayed result.

Use Meta Sentinel as the first end-to-end integration target because it is the primary product and has the original live-camera concept.

Do not delay the other products unnecessarily: Agent 3 can prepare the Ember and Sanitas test datasets and product-specific logic in parallel.

Phase 3: Extend to all three products

* Add Sentinel event assessment.
* Add Ember fire and smoke assessment.
* Add Sanitas sanitation inspection.
* Reuse verified infrastructure.
* Keep product-specific evaluation separate.

Phase 4: Validate

* Run the test suites.
* Measure performance.
* Investigate false alarms.
* Fix critical bugs.
* Verify real model integration.
* Confirm all demonstrated functionality works.

Phase 5: Submission

* Freeze major features.
* Rehearse the demonstration.
* Verify the submission requirements.
* Prepare the technical explanation.
* Clearly document limitations and measured results.

Set realistic checkpoints after repository inspection. Reserve sufficient time for integration and final testing.

## 14. REQUIRED FIRST RESPONSE

Before making major changes, inspect the actual project state and report:

1. What currently exists in the repository.
2. Which relevant Meta AI capabilities and APIs are available.
3. The proposed architecture for all three products.
4. How shared components will be reused.
5. The responsibilities and integration contracts of the four agents.
6. The first end-to-end milestone.
7. The acceptance criteria for proving that milestone works.
8. The highest-risk technical assumptions.
9. The schedule for delivering and testing all three prototypes before the deadline.

Then begin execution.

Do not spend excessive time planning. Once the critical technical assumptions are verified, implement the working system.

Do not ask the developer to restate information already contained in this brief. Ask only for missing credentials, access, or decisions that materially block implementation.

## FINAL OBJECTIVE

Build three specialized, functional public-sector AI applications:

* Meta Sentinel for the NYPD: visual incident awareness and evidence-supported event assessment.
* Meta Ember for the FDNY: visual fire and smoke hazard awareness.
* Meta Sanitas for the Department of Sanitation: visual sanitation inspection and environmental maintenance support.

Share infrastructure intelligently, integrate Meta AI technology meaningfully, and validate each application's real capabilities.

The goal is not merely to show that an AI model can describe an image. The goal is to demonstrate a usable system that turns visual inputs into structured, reviewable assessments and measures how well those assessments perform.

Build what works. Test what you build. Report what the evidence actually supports.
