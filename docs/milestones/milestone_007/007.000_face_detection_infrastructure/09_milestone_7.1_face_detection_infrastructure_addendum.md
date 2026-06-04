Build a small fix pass for Milestone 7 face detection.

Goal:

Correct YuNet output parsing and bounding box validation before moving on to later face milestones.

Problem observed:

\- confidence_score values in the database are unrealistically large (hundreds)

\- some bounding boxes have suspicious values such as negative y coordinates

This suggests the YuNet output array is being parsed incorrectly and boxes should be clamped to image bounds.

Required fixes:

1\. Verify YuNet output layout

\- confirm which indices correspond to:

\- bbox_x

\- bbox_y

\- bbox_width

\- bbox_height

\- confidence_score

\- update parsing accordingly

\- confidence_score should be stored as the actual detector confidence value

2\. Bounding box clamping

Before storing boxes:

\- clamp x and y so they are not negative

\- ensure width and height do not extend past image boundaries

\- keep stored values as integers in original-resolution pixel space

3\. Validation

Update the runner/check flow so we can verify:

\- confidence scores are in a realistic range

\- no negative coordinates remain

\- face boxes still look plausible

4\. Keep scope tight

\- do not change database schema unless absolutely necessary

\- do not add recognition

\- do not add clustering

\- do not change rerun behavior

What to explain after coding:

1\. what YuNet output layout was confirmed to be

2\. what parsing changed

3\. how bounding boxes are clamped

4\. sample corrected output
