## brainstorming

a quick cli app to manage tasks.

name hasnt been decided. please help. => "tk" would be good. i like "tasq," one of claude's suggestions, but it's all left hand and makes the X mark.

should i be asking you to update this document once we start implementation? should this rather be a one shot doc that will be deleted as soon as code is there? => ok, i will only update it myself. i wont ask you to update it. i wont delete it.

i have tasks in README.md. i manually move them to other sections ("done" and "declined" for now) once they are handled. have a look at shared repo's root README.md please.

this is manageable for now, but soon things will get complicated.

i want to simplify this while still having the pending/done/declined task lists then in TODO.md or TODOs.md. should the file name be singular? => ok, singular it is.

TODO.md will be git version controlled. probably i'll do the same with the backend data files of the new cli app, which i think will be in json.

technically i'll be checking 2 sets of diffs for the same data, but if json files are good, i probably wont even check diffs of TODO.md files as they are auto generated.

what would be a good name for this app? the language will be python.

please read stuff in transition-guide folder for my coding preferences.

how to load/save app-wide config, user settings, optional parameters, etc havent been decided. there should be a set of my personal guidelines for that, i think. what would you suggest? => this too depends on the app. i will not make any guidelines and will remain flexible. i will explain my decisions on this very app later in this document.

i wont write shared libraries (as i would have for c#) so that ais can make better decisions.

as for data, timestamps should be in utc. when task is registered and when it is handled.

task should be one paragraph. no linebreaks. it can be one sentence or more. whether to finish each sentence with a period or not is optional. a list item often doesnt end with a period if the content is one clause (if i am calling it right). then, if a task contains multiple sentences, we can choose to finish each sentence with a period or use periods more like separators of the sentences and omit the one in the last sentence. i dont think consistency here is going to add value.

we should be able to add a simple note or "results" or "remarks" or whatever you think to be the right term for each task upon handling. this is not to make the task more informative. for this purpose, we should just squeeze minified explanation into the task itself (or make a document elsewhere and mention it). the additional thing is strictly only for mentioning how it has been handled and why.

then one trivial feature i would like to add is time management related. i currently live in japan where the time is 9 hours ahead of utc. and i usually wake up at 4 am as i can work usually only until 2 pm for family-related reasons. but sometimes i stay up longer. 1 am, 2 am, etc. very rare, but possible. it is a reasonable option to define that a "subjective day" is since the person wakes ups and until the person sleeps. my subjective day is from 4 am to 3:59 am on the next calender day. i want to be able to set the user's time zone and the time the user's subjective day starts. then my work at local-time 11 pm and some more at local-time 1 am will be grouped into the same subjective day in TODO.md. these subjective days will not be consistent with possible readers', but that wont hurt. this is merely for handled-task grouping.

if we can also set the subjective handling date manually, it would be perfect. like my current TODO.md already contains a few tasks i have finished yesterday. when the app is ready, if i just add them again and immediately "handle" them, they will be today's work. also, sometimes i will only finish work and then attend to other matters and fail or forget to mark the tasks as handled. in such a case, i would need to set the handling date one day before on the next day. such human errors cant be completely avoided. so, we'll let the feature take care of that.

sorting is by subjective dates and then timestamps. what i do and decline on the same day are sometimes related. so, unlike the current structure of README.md, grouping should be "todo" first (where newer tasks appear later), "handled" that is then grouped into subjective dates in descending order, meaning later work appears sooner. in each subjective date group, tasks are in ascending order, meaning later work appears later. when we check pending tasks, we should have to see old ones first as we are not acting on them for some time and should decide what to do. when we refer to handled tasks, new work matters more so dates must be in descending order. in each group, first work comes first.

anything else? => in response to claude's questions: yes, tasks are editable. full crud operations supported. TODO.md will be auto generated on each crud operation. this is a personal tool. at least for now, it is good enough to use TODO.md as the view. the tool should be able to support "list" sub command or something similar, but filtering can wait. let's start small. for this reason, i didnt mention setting priority levels or due dates. simple + fast often make more value. so, no searching. when referencing a task in a update/delete operation, we'll use numbers starting with 1. i thought about giving an uuid to each task upon registration, but nothing in the app or the outside will link to the tasks for now. so, we can auto-generate them only if we actually need them.

"list" and "history" will add numbers to the tasks. we can edit anything. to make it intuitive, "done" and "decline" and the update/delete operations all take one of the numbers of previously displayed list/history. "add" adds the new task at the end of the list, not changing the order of existing tasks. part of me wants to then edit one or more tasks without displaying list/history again. like we have 3 tasks, show a list, edit 1st, add one, edit 3rd (which was 3rd and is still 3rd) and delete 4th (the new one) and edit 2nd; we dont really need to reload the list for this. should we support this stateful operations? or should we allow task editing (and therefore task number taking) operations only immediately after list/history commands? => ok, agreed on stateless design. number taking operations only right after list/history. 

---

this is a profile based app. system/use agnostic settings should be preset in one file and be given to the app. here i say "profile" to make sure the concept wont get related to any of app-wide config or user settings or additional/overriding options specifically. if there's a better word, i would like to know it.

a "profile" file will be a json or maybe yaml/ini file that will contain: absolute or to-be-mapped relative path to backend json file, path to auto generated file, time zone, subjective day start time (not just hours. hours and minutes at least).

one design flaw i have noticed is that handling subjective date in the handled task entry is not optional. upon task handling, depending on the current time zone, current subjective day start time and current computer clock time, app needs to immediately finalize the subjective handling date. otherwise, once i go abroad and modify time zone in the profile, data integrity will be lost.

---

again in response: this app will be stateless, but in a way we'll be in a state as we run tk command with a file path with or maybe without the "--profile" or "-p" for short specifier once and then we are in the app until we leave it with a command. so, this will be a interactive/repl app.

tk new or tk init or whatever you suggest should make a new profile, using current time zone and my favorite 4 hours and 0 minutes and 0 seconds subjective day starting time.

regarding the to-be-mapped relative path i have mentioned, i forgot to say: ~ is mapped to user directory. @ is mapped to app directory, most naturally where the toml file will be (so shared/apps/tk). current directory wont be supported. unreliable. this app will read and write files. current directory cant decide where they will be. if we support these 2, 90% of cases can be handled. remaining 10% - we'll just ask "should we really be this particular?"

as for the json or yaml or ini question, json for any settings-related things should be one viable strategy. appsettings.json for example handles very complex data beautifully. this app's profiles will be simple, but some of my future apps will require structured profile data. so i'll go get some ice cream to brain freeze myself and use json for profiles simply and consistently because profiles are settings related.

when we load a profile as well, if not absolute, we need to map the path.

and i am getting used to calling it a "profile." so let's make it official unless profile in english strictly means info on a specific human being.

as for subjective day start time, hh:mm is enough, but some people including myself 3 weeks later may write hh:mm:ss without thinking much. writing just the hours like "4" is counter intuitive and most people wont do it. so, if we support 2 formats, just enough.

let's use __init__ and __main__ and "c#-ish but not too anti-pythonic, soc-preferred, well-balanced design" that will be installable as a package via poetry.

---

regarding folder structure: your suggestion to make "tk" right under "tk" doesnt sound correct. let's at least make it tk/src/tk so that tk/tests can be added naturally. using "tk" twice feels wrong, but if that is ok in python world, let's do it. if not, "tk/src/tkapp" or "tk/src/tkcli" may be good options.

## after initial implementation

the "new" sub command is mentioned like "tk> new" in readme.md, indicating new works after the user is in the repl mode. "new" should work before. otherwise, user has no profile to use. "tk new ~/work/my-profile.json" without the ">" symbol should make the profile.

---

"tk new" too should take --profile or -p explicitly (if -p is supported).

---

"poetry run" worked. i got "timezone: etc/gpt+9". why etc, not jst? my mac's config says jst. so i'm guessing it's not that mac has its own timezones defined and doesnt recognize jst. i would like to know what etc means and whether i should manage to get jst instead.

in tasks.json, next_id is set to 1, which is probably a major inconsistency. if we need to give at least one id-ish thing, we should reconsider giving an uuid for extensibility. we dont need simple numbers preassigned to tasks for list/history as they would then show non-sequential numbers. merits of not assigning any id-ish things to tasks is currently significant as task lists will be version controlled.

---

when app loads profile, app should display timezone, whether dst is applied or not, actual time and subjective time start time. user should make it a habit to check these.

add, decline, etc may feel redundant eventually. "a" for add, "d" for "done", etc should work. let's change "decline" to "cancel." then "c" will work for "cancel". "l" for "list" and "h" for "history." please make sure all commands are supported.

when list/history is called, if you havent implemented this, let's check the number of items we are about to display and use the right string format for the numbers so that [ ] will be vertically aligned. like if we have 10 tasks to show, first one should be " 1" with leading padding.

do we have a command that sets/updates/removes note to/from a task?

also, can we set subjective handling date when we handle/update task?

any part of anything should be editable anytime. please make sure.

then let's implement confirmation. when we handle/update task, we need to know what we are about to do before we do it and be able to cancel it. especially planned subjective handling date must be checkable.

probably, it'll be simpler if app asks for a note if unset and asks for handling date if user is marking the task done or cancelled. in each prompt, enter key should mean user has no intention to set it.

we should also display an empty line after each command. like when task has been added, list has been displayed, etc.

---

there's no short form for "delete". let's document it. task deletion is dangerous. also, it is rarely needed. if we dont like a task, we can cancel it.

profile should have 2 sync related settings. one is whether to sync every time when backend data is changed. default should be true. safer is better. the other is whether to sync before app closes. default should be false. if each event syncs, app closure time sync is redundant.

let's document we dont check if task already exists when we are adding/editing one. if we use ai to meaningfully check that, it might be useful. if we only compare strings, it wont catch much and will only complicate the code.

---

in todo.md, done tasks and cancelled tasks are separated. they must be merged. title of document must be "TODO". after an empty line, the pending task list without a heading. then "## History" in respect to the tool's command. then an empty line follows and the date heading. i dont think we need an empty line between a date heading and its tasks. between date-based groups, we need an empty line.

before task deletion, app needs to confirm.

is there a way to make edit/note commands cancellable? like by using a shortcut key. if that is possible, we can omit the final yes/no question of done/cancel commands.

should we use a package to enable editable input so that user wont have to retype stuff when editing task/note? how complicated will app be? if editable input is hard to fully control, we probably dont need to bother.

after close/exit, let's output an empty line so that the following prompt will start anew.

---

when user quits, let's show statistics. just how many tasks are pending, how many have been done and how many have been cancelled.

## code review after initial testing

in markdown.py, let's emit an empty line after "# TODO". then, if there's no pending task, let's emit a short message. we will show the history part only if at least one task has been handled. otherwise, we emit one new line after the pending task list and file ends. if there are handled tasks, after "## History", let's emit an empty line. at the end of the file, there should be an empty line. this is just a personal preference. if "end" key combined with something gets me to the last empty line, rather than the last position of the last line, i find it easier to add new content.

when app reads/writes a file, we should always specify utf-8 encoding but without bom. cjk letters are often broken in non-utf8 files.

profile.py reads system timezone in multiple ways. is the timezone detection mechanism optimal? if "asia/tokyo" and such are more mac-ish things and python fully supports abbreviations like jst, shouldnt we rather try getting the system timezone as an abbreviation so that the app will run on windows as well?

---

in todo.md, let's use " => " to output note like my current readme.md at repo root. in a parenthesis, note might look like additional info on task. it is basically "how the task went".

in profile.py, how likely will hasattr succeed? i'll never run the app on old python. if it is highly likely, we dont need the premature mapping logic.

app calls the markdown output file as "TODO.md". we cant assume the file name will always be TODO.md. let's fix it. also, let's look for such literals embedded in code and, if they might actually differ from user-facing strings (and ONLY if), let's fix them.

in cli.py, "edit" joins most of args, but "note" doesnt. is this ok?

## bug fixes and improvements after code review

add "my task" and add my task both work, but add what's python's protocol? works incorrectly as the 2 apostrophes are dropped. in this app, any text that may contain 2 or more words is at the end of the command line. so, let's consider omitting quotation support completely.

instead of [ ], [x] and [~], let's use unicode emojis as [~] isnt supported even on github. please suggest a few combinations.

---

currently, "history --days 3" for example should display handled tasks on today, yesterday and day before yesterday. so, last 3 CALENDER days, not last 3 WORKING days.

let's add an exclusively effective option --working-days. --days and --working-days cant coexist. only one can be specified.

then let's add 3 commands: today, yesterday, recent. if "t", "y" and "r" are all available, let's implement these as well. today and yesterday are obvious. recent returns the last 3 WORKING days including today. i believe i'll be hitting "r" all the time to know what i have been doing so that i can decide what to do next.

history shows the old [ ], [x], [~] things. when saving data as markdown, app no longer does this and uses emojis instead for handled tasks. let's use emojis in history to make it consistent.

in "list", we dont need [ ] or any emojis. a simple numbered list is sufficient.

---

we dont need to say "statistics: " when we show the statistics. kind of obvious.

"tk new" makes a new profile. let's change it to "tk init". "new" is a very useful word. i want to reserve it for more frequently new-ed things.

---

from vertex, i got:

title: nodewave.io
url: https://www.nodewave.io/blog/top-ai-models-2026-guide-compare-choose-deploy

if title is a host name and is completely contained in the url, let's set None to title.

please search the web to confirm this is a good workaround.
