1\. Software-based scan detection

Use A.

Add a nullable raw software field to Asset and use it in normalization.

Reason:

\- the milestone explicitly calls for software-based scan detection

\- it keeps the heuristic more accurate

\- it preserves useful raw metadata for later logic

2\. Schema update approach

Yes, use the same approach as Milestone 3.

Reason:

\- keep it simple and consistent

\- update the model

\- reset/recreate local schema with init_db.py --reset

\- rerun ingestion and EXIF extraction before running normalization

\- do not add migrations yet
