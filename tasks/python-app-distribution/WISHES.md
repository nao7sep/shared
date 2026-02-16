## pypi

please find poly-chat in shared repo. i would like to distribute it via pypi. along the way, i would like to learn about relevant services including github actions. should i automate everything? i am new to python. i might feel more comfortable editing pyproject.toml with a new version number only when i feel the new code is good enough for release AND manually push it to pypi (if that is how it works), but i am usually wrong when i wish to stick to old ways. please tell me everything people do.

---

i have never used git tags. needing to call "git push --tags" indicates files and tags are separate. are tags more like attributes? you said: git commit => git tag => git push => git push -- tags. can the order be different? also, what if the git tag version differs from the one in pyproject.toml?

how can i exclude/relocate files contained in the project directory? like completely exclude docs/shame.md and rename docs/my-super-cool-notes.md to docs/notes.md?

am i correct to assume my local directory structure (of the app) is exactly what users will have when they install the app? i wont do this, but if i use cjk chars in file system object names, should they be replicated on users' computers? what are the limits/restrictions?

should i use testpypi? if there's a very high chance that my first attempt can be a good attempt, i would prefer to be lazy.

---

ok, i'm already lazy. can we develop a mini tool, following the directory structure of poly-chat, that will ask for a version number string, update pyproject.toml (and relevant files), commit the version number only diff, set a tag, push the file(s) and push the tag? github actions will automate things AFTER the tag is pushed, right? is there a standard tool for what i am thinking about too?

poly-chat has some builtin prompts as files. they are in poly-chat/prompts while the app is in poly-chat/src/poly_chat. within the app, the paths to them are handled with the @ symbol, that maps relative paths to the app directory (where pyproject.toml exists). like, @/prompts/system/default.txt. i am guessing i need to move them to poly-chat/src/poly_chat/prompts. i wonder what will happen for @/* paths. please investigate the code.

---

you made tools/release.py and publish-pypi.yml and publish-testpypi.yml in .github/workflows.

should i install github actions extension to vsc? should the github files be exactly where they are (poly-chat/.github/workflows)? is it correct to assume release.py only does the local git work and then github actions on the server side will find the workflow files and publish the app IF a corresponding tag is found?

---

the workflow files have been moved to repo root. does that mean they will work for ANY apps i will add in the future? even for ones in different programming languages?

---

so, github actions isnt exactly designed for a mono repo with many apps. if i stick to github actions, i'll have to use app-name-included tags, right? and, there is a chance that apps in different languages or with a different structure may be handled incorrectly too.

let's switch to a python script based manual distribution that uses the poetry command. i will use github actions for one-repo-per-app apps. suppose i take responsibility for the version number in pyproject.toml, the script will need to parse pyproject.toml, extract the version number and run the poetry command to distribute the app. is this the right workflow? what else will the script do?

---

i have pypi/testpypi accounts with 2fa enabled. i have made 2 tokens for "poly-chat" and registered them via the "poetry config" command like:

cd ~/code/shared/apps/poly-chat
poetry config pypi-token.pypi pypi-YOUR_TOKEN_HERE
poetry config pypi-token.testpypi pypi-YOUR_TESTPYPI_TOKEN_HERE

then,

# Build only (safe, no publishing)
python3 tools/publish.py --build-only

succeeded and 2 files were created.

before i run:

# Publish to TestPyPI (recommended first)
python3 tools/publish.py --test

# If TestPyPI works, then publish to PyPI
python3 tools/publish.py --prod

let's clarify a few things:

1. should i commit files in dist directory? is there a way to specify where to create contents of this directory from next time? if an experienced user wants to try poly-chat, they should clone the repo. if the user is not that experienced, pip/pipx should be easier. what do people do with dist directory?

2. is there a way to check if poly-chat's dependencies are actually needed? i switched from google-generativeai to google-genai. unlike c#, references seem more explicit in python (probably because versions must be locked). in C#, if we need package A and if package A depends on package B, if we no longer need package A and delete it from the .csproj file, package B is no longer referenced. but in python, if we need package A, just to lock the version of package B, package B is referenced in pyproject.toml. or, maybe i am understanding something incorrectly. question is: how do we make sure users wont get what they dont need? optionally, how do we automate this sanitization?

3. is the current state of pyproject.toml correct? will prompt files be included? poly-chat doesnt have a project-level .gitignore. are things like __pycache__ properly ignored?

4. is poly-chat really ready to work with different app root directory paths?

5. when i made pypi/testpypi tokens, i made them effective in the entire scope or something as instructed. i guess i will need to update their settings after first uploads. how should i do that?

6. how do we deal with LICENSE and app root README.md? i read somewhere that the project page on pypi/testpypi could be generated from README.md. should we? or, should we prepare a more pypi/testpypi suitable shorter version? current README.md is quite large.

7. i also read that once a package was uploaded, the same version number could never be used. it's a reasonable design for security. can we at least delete uploaded packages? we just cant use the same version numbers again even if we delete the packages, right? if first attempts tend to fail, maybe i should start with 0.0.1. is this a "correct" version number in the semantic versioning system?

---

if you were to add dist/ to my repo root .gitignore, which category would you choose? i am curious because other programming languages too may use this directory name.

please make sure "transitive dependencies" as you call are not explicitly imported by pyproject.toml.

if you are to make .gitignore in app directory, please make it minimal. basically, only what we have already needed to ignore. i dont like .gitignore that ignores everything from day 1. the repo root .gitignore may be helpful.
