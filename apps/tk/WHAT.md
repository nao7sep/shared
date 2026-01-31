a quick cli app to manage tasks.

name hasnt been decided. please help. => "tk" would be good. i like "tasq," one of claude's suggestions, but it's all left hand and makes a X mark.

should i be asking you to update this WHAT.md once we start implementation? should this rather be a one shot doc that will be deleted as soon as code is there? => ok, i will only update it myself. i wont ask you to update it. i wont delete it.

i have tasks in README.md. i manually move them to other sections ("done" and "declined" for now) once they are handled. have a look at shared repo's root README.md.

this is manageable for now, but soon things will get complicated.

i want to simplify this while still having the pending/done/declined task lists then in TODO.md or TODOs.md. should the file name be singular? => ok, singular it is.

TODO.md will be git version controlled. probably i'll do the same with the backend data files of the new cli app, which i think will be in json.

technically i'll be checking 2 sets of diffs for the same data, but if json files are good, i probably wont even check diffs of TODO.md's as they are auto generated.

what would be a good name for this app? the language will be python.

read stuff in transition-guide folder for my coding preferences.

how to load/save app-wide config, user settings, optional parameters, etc havent been decided. there should be a set of my personal guidelines for that, i think. what would you suggest? => this too depends on the app. i will not make any guidelines and will remain flexible. i will explain my decisions on this very app later in this note.

i wont write shared libraries (as i would have for c#) so that ais can make better decisions.

as for data, timestamps should be in utc. when task is registered and when it is handled.

task should be one paragraph. no linebreaks. it can be one sentence or more. whether to finish each sentence with a period or not is optional. a list item often doesnt end with a period if the content is one clause (if i am calling it right). then, if a task contains multiple sentences, we can choose to finish each sentence with a period or use periods more like separators of the sentences and omit the one in the last sentence. i dont think consistency here is going to add value.

we should be able to add a simple note or "results" or "remarks" or whatever you think to be the right term for each task upon handling. this is not to make the task more informative. for this purpose, we should just squeeze minified explanation into the task itself (or make a document elsewhere and mention it). the additional thing is strictly only for mentioning how it has been handled and why.

then one trivial feature i would like to add is time management related. i currently live in japan where the time is 9 hours ahead of utc. and i usually wake up at 4 am as i can work usually only until 2 pm for family-related reasons. but sometimes i stay up longer. 1 am, 2 am, etc. very rare, but possible. it is a reasonable option to define a subjective day is since the person wakes ups and until the person sleeps. my subjective day is from 4 am to 3:59 am on the next calender day. i want to be able to set the user's time zone and the time the user's subjective day starts. then my work at local-time 11 pm and some more at local-time 1 am will be grouped into the same subjective day in TODO.md. these subjective days will not be consistent with possible readers', but that wont hurt. this is merely for handled task grouping.

(now i am reading this myself and think this subjective day thing will be useful in other apps. i'll one day try a prompt like "read WHAT.md of "tk" and apply the subjective day thing please").

if we can also set the subjective handling date manually, it would be perfect. like my current TODO.md already contains a few tasks i have finished yesterday. when the app is ready, if i just add them again and immediately "handle" them, they will be today's work. also, sometimes i will only finish work and then attend to other matters and fail or forget to mark the tasks as handled. in such a case, i would need to set the handling date one day before on the next day. such human errors cant be completely avoided. so, we'll let the feature take care of that.

sorting is by subjective date and then timestamps. what i do and decline on the same day are sometimes related. so, unlike the current structure of README.md, grouping should be "todo" first (where newer tasks appear later), "handled" that is then grouped into subjective dates in descending order, meaning later work appears sooner. in each subjective day group, tasks are in ascending order, meaning later work appears later. when we check pending tasks, we should have to see old ones first as we are not acting on them for some time and should decide what to do. when we refer to handled tasks, new work matters more so dates must be in descending order. in each group, first work comes first.

anything else? => in response to claude's questions: yes, tasks are editable. full crud operations supported. TODO.md will be auto generated on each crud operation. this is a personal tool. at least for now, it is good enough to use TODO.md as the view. the tool should be able to support "list" sub command or something similar, but filtering can wait. let's start small. for this reason, i didnt mention setting priority levels or due dates. simple + fast often make more value. so, no searching. when referencing a task in a U/D operation, we'll use numbers starting with 1. as a c#er, i rather seriously thought about giving an uuid to each task upon registration, but nothing in the app or the outside will link to the tasks for now. so, we can auto-generate them only when/if we actually need them.

"list" and "history" will add numbers to the tasks. we can edit anything. to make it intuitive, "done" and "decline" and the U/D operations all take one of the numbers of previously displayed list/history. "add" adds the new task at the end of the list, not changing the order of existing tasks. part of me wants to then edit one or more tasks without displaying list/history again. like we have 3 tasks, show a list, edit 1st, add one, edit 3rd (which was 3rd and is still 3rd) and delete 4th (the new one) and edit 2nd; we dont really need to reload the list for this. should we support this stateful operations? or should we allow task editing (and therefore task number taking) operations only immediately after list/history commands? => ok, agreed on stateless design. number taking operations only right after list/history. 

one thing i think i should add is that the task lists are merely for doing things and NOT feeling "Yay, I'm greeeat!" so if i "dont think, just do," i wont add a task and immediately "handle" it just to leave it in the log. so TODO.md wont be a full list of work. in this vibe coding era, processes are often cluttered. we only need to do-do-do to get work done is what i am starting/trying to think.

---

i have considered restructuring this document into a proper one with or without ai assistance and declined this thought as it would go back in time to the ancient waterfall workflow. this is vibe coding. this WHAT.md is the vibe. so, we'll Keep-It-Stupid-and-Stupid. with ais being far smarter than i am and handling messy things in seconds, simplicity is not always worth spending time for. this messy WHAT.md is the result of thinking and writing in parallel. i'd like to delegate the simplification and refinement work to ais.

in response to your latest questions: this is a profile based app. system/use agnostic settings should be preset in one file and be given to the app. here i say "profile" to make sure the concept wont get related to any of app-wide config or user settings or additional/overriding options specifically. if there's a better word, i would like to know it.

a "profile" file will be a json or maybe yaml/ini file that will contain: absolute or to-be-mapped relative path to backend json file, path to auto generated file, time zone, subjective day start time (not just hours. hours and minutes at least).

one design flaw i have noticed is that handling subjective date in the handled task entry is not optional. upon task handling, depending on the current time zone, current subjective day start time and current pc clock time, app needs to immediately finalize the subjective handling date. otherwise, once i go abroad and modify time zone in the profile, data integrity will be lost.

---

again in response: this app will be stateless, but in a way we'll be in a state as we run tk command with a file path with or maybe without the "--profile" or "-p" for short specifier once and then we are in the app until we leave it with a command. so, this will be a interactive/repl app.

tk new or tk init or whatever you suggest should make a new profile, using current time zone and my favorite 4 hours and 0 minutes and 0 seconds subjective day starting time.

regarding the to-be-mapped relative path i have mentioned, i forgot to say: ~ is mapped to user directory. @ is mapped to app directory, most naturally where the toml file will be (so shared/apps/tk). current directory wont be supported. unreliable. this app will read and write files. current directory cant decide where they will be. if we support these 2, 90% of cases can be handled. remaining 10% - we'll just ask "should we really be this particular?"

as for the json or yaml or ini question, json for any settings-related things should be one viable strategy. appsettings.json for example handles very complex data beautifully. this app's profiles will be simple, but some of my future apps will require structured profile data. so i'll go get some ice cream to brain freeze myself and use json for profiles because profiles are settings related.

ah, when we load a profile as well, if not absolute, we need to map the path.

and i am getting used to calling it a "profile." so let's make it official unless profile in english strictly means info on a specific human being.

as for subjective day start time, hh:mm is enough, but some people including myself 3 weeks later may write hh:mm:ss without thinking much. writing just the hours like "4" is counter intuitive and most people wont do it. so, if we support 2 formats, just enough.

we use __init__ and __main__ and c#-ish but not too anti-pythonic soc-preferred well-balanced design that will be installable as a package via poetry.

---

now you've said WHAT is complete. i asked for HOW.md, you generated it and i asked whether i should precisely review it or roughly take a look at it or not see it at all for maximum productivity and you told me not to see it at all so that i wouldnt be checking the HOW before tests are run. that is very reasonable. this decision and rationale must be noted here.

but one part of the HOW that i cant help checking beforehand is folder structure. how directories and files are named and placed. your suggestion to make "tk" right under "tk" doesnt sound correct. let's at least make it tk/src/tk so that tk/tests can be added naturally. using "tk" twice feels wrong too, but if that is ok in python world, it is ok. if not, "tk/src/tkapp" or "tk/src/tkcli" may be good options, but this is really just extra thinking.
