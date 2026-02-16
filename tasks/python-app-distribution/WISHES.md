## pypi

2026-02-16:

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
