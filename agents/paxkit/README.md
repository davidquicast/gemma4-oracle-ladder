# paxkit

The 5-minute starter agent (`base_e4b`) plus a check the persona hands over ready-made: one
exact shell command that compiles each changed Python file and runs the existing test file
named after each changed module. The model copies and runs it; it never writes a check of
its own (contrast `paxgate2`, where the model wrote the check and it passed in ~9% of episodes).
