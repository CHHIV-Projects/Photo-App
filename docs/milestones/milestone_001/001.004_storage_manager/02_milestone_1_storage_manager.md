Build the next Milestone 1 module: storage_manager.

Requirements:

\- create a Python module that copies unique files into a vault directory

\- accept deduplicated results as input

\- only process unique files (ignore duplicates for now)

\- copy files to a destination folder (vault path)

\- the vault destination path will be passed in as a function parameter, do not hardcode it

\- - do not overwrite existing files in the destination

\- preserve file contents exactly (no modification)

\- verify the copy by comparing file size before and after

\- handle errors gracefully and collect them

\- return structured results including:

\- successfully copied files

\- failed copies with reasons

\- keep code simple and modular

\- do not connect to the database yet

\- do not delete source files yet

\- include a small test script or instructions for how to run it

\- explain where the file should live in the project structure
