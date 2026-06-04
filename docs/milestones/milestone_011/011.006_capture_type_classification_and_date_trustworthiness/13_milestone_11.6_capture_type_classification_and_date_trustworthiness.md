**Milestone 11.6 — Capture-Type Classification and Date Trustworthiness**

**Goal**

Introduce a **reliable and explainable classification system** that determines whether a photo is:

-   likely a **born-digital photo**
-   likely a **scan/reproduction**
-   or **uncertain**

and, most importantly:

👉 whether the **timestamp should be trusted as the original capture date**

This replaces the simplistic is_scan concept with a more accurate and scalable model.

**🧠 Core Concept**

This milestone is not just about “scan vs digital.”

It is about:

**Can we trust the timestamp on this asset as the real moment the photo was taken?**

This affects:

-   event grouping
-   timeline accuracy
-   metadata interpretation
-   future scan date estimation

**🔵 Primary Outcome**

When complete, the system should:

1.  classify each asset as:
    -   digital
    -   scan
    -   unknown
2.  determine whether capture time is **trustworthy**
3.  allow **manual override** of classification
4.  apply classification consistently across:
    -   photo detail UI
    -   event clustering logic
    -   future timeline features

**🧱 Data Model (Recommended)**

**Replace or extend is_scan**

Instead of only:

is_scan: boolean

Use:

capture_type: "digital" \| "scan" \| "unknown"

capture_time_trust: "high" \| "low" \| "unknown"

**Meaning**

| **Field**          | **Purpose**                                  |
|--------------------|----------------------------------------------|
| capture_type       | what kind of source this is                  |
| capture_time_trust | whether EXIF timestamp reflects real capture |

**🟢 Classification Logic**

**Layer 1 — Metadata Heuristics (Primary)**

Use simple, explainable rules.

**Likely Digital**

-   EXIF camera make/model exists
-   EXIF datetime present and plausible
-   no scan-like software tags

**Likely Scan**

-   missing camera make/model
-   EXIF created/modified date exists but no capture metadata
-   software indicates:
    -   scanning app
    -   image editor
    -   mobile scan app (e.g., Photomyne-style)
-   resolution/aspect typical of scanned prints (optional)

**Unknown**

-   mixed or insufficient signals
-   conflicting metadata

**Layer 2 — Trust of Capture Time**

**High Trust**

-   EXIF capture date exists and is plausible
-   consistent with camera metadata

**Low Trust**

-   likely scan
-   capture date missing or equals file creation/import time
-   metadata inconsistent

**Unknown**

-   insufficient signal

**Layer 3 — Manual Override**

Provide backend capability to override:

{

"capture_type": "scan",

"capture_time_trust": "low"

}

Manual override must:

-   persist
-   not be overwritten by reclassification scripts

**🟡 Backend Requirements**

**1. Extend Asset Model**

Add fields:

-   capture_type
-   capture_time_trust

(If you prefer to keep is_scan, it can be derived from capture_type == "scan".)

**2. Classification Function**

Add service logic:

classify_asset_capture_type(asset) -\> capture_type, capture_time_trust

Used in:

-   ingestion pipeline
-   reclassification script

**3. Reclassification Script**

Add script:

python scripts/reclassify_capture_type.py

Behavior:

-   iterate over assets
-   apply classification rules
-   update fields
-   respect manual overrides

**4. API Updates**

Extend photo detail response:

{

"capture_type": "scan",

"capture_time_trust": "low"

}

**🟠 Frontend Requirements**

**1. Replace “Type” display**

In Photo Detail panel:

Instead of:

Type: Digital

Show:

Type: Digital \| Scan \| Unknown

Capture Time: High Confidence \| Low Confidence \| Unknown

**2. Keep UI simple**

-   no complex indicators
-   just readable labels
-   no icons required

**3. Optional (if trivial)**

Add small manual override control:

-   dropdown or toggle
-   only if easy to implement

Otherwise skip for now.

**🔴 Event System Impact**

Use new classification:

-   if capture_time_trust = low  
    → do NOT rely on timestamp for event grouping
-   if capture_type = scan  
    → continue using provenance-based grouping (11.3)

**🧪 Validation Checklist**

Verify:

1.  known scans classified as scan
2.  digital camera photos classified as digital
3.  ambiguous cases fall into unknown
4.  capture_time_trust reflects reality
5.  event grouping improves for scans
6.  manual override persists correctly
7.  UI reflects updated classification

**🧠 Guiding Principles**

1.  Prefer **correct + uncertain** over **incorrect + confident**
2.  Use **simple heuristics first**
3.  Keep classification **explainable**
4.  Never overwrite manual decisions silently
5.  Focus on **date trust**, not just file origin

**❌ Do NOT include in this milestone**

-   OpenCV-based image analysis
-   ML models (PyTorch, TensorFlow, etc.)
-   OCR-based date extraction
-   full provenance history
-   duplicate merging
-   timeline UI

Those belong later.

**🧭 Position in Roadmap**

This milestone enables:

-   accurate event grouping
-   future timeline features
-   scan date estimation
-   better metadata trust

**🔑 Summary**

This milestone shifts the system from:

scan vs digital (naive)

to:

capture type + date trust (robust and scalable)

**Suggested Commit**

git commit -m "Milestone 11.6: Add capture-type classification and capture-time trust model"
