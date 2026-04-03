Build the next Milestone 1 module: hasher.

Requirements:

\- create a Python module that computes SHA-256 hashes for accepted file records

\- accept a list of FileScanRecord objects as input

\- return structured results that include:

\- the original file record

\- sha256 hash

\- process files safely in chunks so large files do not load fully into memory

\- handle file read errors gracefully and collect them separately

\- keep code simple and modular

\- do not compute pHash yet

\- do not connect to the database yet

\- include a small test script or instructions for how to run it

\- explain where the file should live in the project structure
