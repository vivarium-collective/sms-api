- [x] 1. `app/gui.py`: create a marimo in this directory which serves as a GUI whose exposed functionality encapsulates that exactly of the atlantis cli (full e2e EUTE workflow.)

### Notes:

- keep in mind when developing this, the following info: a. I need the aesthetic/design/theme of this gui to very much actually be what we discussed previously: a highly colorful yet clearly readable, 
memphis-design and https://static.wikia.nocookie.net/logopedia/images/7/7a/Mapquest_logo_old.png/revision/latest?cb=20100630203131 inspired, UI using marimo and wigglystuff (see both repos for more details) such that
flexes the two packages as much as possible to match what I want. Harmonize with me here and realllly understand this: the general aesthetic and feel of this UI theme/vibe in general should match the following vibe (THEME below,) for 
the following scenario (SCENARIO below):


[SCENARIO:] We are building aaa video game in 2026 that is a dystopian biological sci-fi at a research company set in the 90s (NOTE: this is exactly where the sms-api comes in). Particularly we are designing ui in the game that is extremely similar, but not the same as, Fallout's Pip Boy, which in the game was created
As a revolutionary new product by the research company. In the story, this 
device, called "atlantis" was designed by memphis-design (like IRL memphis-design group style: early 90s bright colors, lots of smooth curves, few yet contrasting angles - in elements, etc). Actually in the game, memphis-design was contracted to have the theme use 
the exact same theme/elements from the following memphis design pattern: https://as2.ftcdn.net/v2/jpg/01/04/80/65/1000_F_104806545_dnc4vKKdqwJ6rBtT7r142hdVVLZoBGEf.jpg . Obviously, the entirebackground of the ui cannot be just that image/repeated pattern in fullscreen, thus
it should be very sleekly, prominently yet perfectly placed (as a thin yet full width banner, as one instance among others.) Also, in the game's universe, marimo and wigglystuff exist in the 90s and have also been contracted by the research company to actually be the UI framework for atlantis, thus the aformentioned 
memphis design pattern (specific one mentioned, AS mentioned in terms of usage/placement/UX) by marimo with wigglystuff as an asset.

KEEP IN MIND:
- Other inspirations aestethically include: Rocko's modern life, clayfighter 3d, and the following font: https://static.wikia.nocookie.net/logopedia/images/7/7a/Mapquest_logo_old.png/revision/latest?cb=20100630203131
- When people are often designing a "retro" ui like this, they obviously resort to including a pixelated feel as one of the aesthetics...THIS UI SHOULD NOT, within reason, because in the game's universe marimo and wigglystuff is the framework used, and their aesthetic is modern. THIS IS EXACTLY WHAT I WANT!!!!
I want an EXTREMELY sleek/impressive/easy-to-use, highly modern UI, with extremely tasteful uses of the entire, extremrely important early/mid 90s aesthetic as ACCENTS in the modern ui (buttons, banners (it should be a sleek strip, not wide!!), info, etc).
- Please generate a new test module tests.app.test_gui_app containing marimo-friendly (see their docs), robust and thorough e2e & unit tests which thoroghly and demonstratably tests this gui_app.
- Once finished, please ensure make check passes, but dont commit.

- [x] 2. Lets remember that the sms api currently has 2 different compute backends: aws batch in govcloud with s3 (`sms-api-stanford-test` namespace) and SLURM with Hpc filesystem hosted on our prem (`sms-api-rke`). With that said, let's ensure that now that we have made progress with the batch stuff, that the SLURM stuff is not broken: please verifiably ensure first that app.cli works completely for full e2e workflow end-user functionality when --base-url is set to https://sms.cam.uchc.edu (the sms-api-rke base url, what i will refer sometimes to ccam or CCAM) for all relevant operations. 
If this full e2e test of cli on ccam reveals fixes, please ensure the fix not only propogates to make the cli work ( internal services/modules etc ), but also update the tests as needed.

- [x] 3. Adjust the parameterization of the /api/v1/simulations <POST> endpoint such that an optional parameter called "observables" is a flat array of dot separated vecoli output paths, where the dot is the path heirarchy sep that in that /api/v1/simulations <POST> endpoint's handler, if passed in the request, get properly formatted/transformed in the
correct way for vEcoli's engine_process_reports JSON config attribute as we are discussing. So for example, if the user expects to only report ["boundary", "external", "mecillinam"], ["bulk"] in the engine_process_reports attribute, their request would contain an "observables" attribute whose value is ["bulk", "boundary.external.mecillinam"].
Make sure that robust yet optimally sized/scoped tests exist and update existing if needed. Once this is tested and works, ensure that the following content is thoroghly updated for those changes, and really the exactly current repo state if needed: app.cli app.tui app.gui docs/ README.md, and whatever else might be effected. 
when complete, (in the same way weve been doing: stage command, commit command (just a single line commit)) group and suggest commits. Finally, update the coworker-sharable knowledge and context as needed.

- [x] 4. The GET /api/v1/simulations/{id}/log endpoint transfers the entire Nextflow stdout, which grows large for big simulations and slows down `atlantis simulation status`. Fix this SERVER-SIDE: add an optional `truncate` query param (default true) to the log endpoint. When true, the handler returns only the head (first ~20 lines: Nextflow version + launch info) concatenated with the tail (last block starting from the final `executor` line to EOF), separated by a `... truncated ...` marker. This reduces the response payload from potentially MBs to a few KB. The full log remains available via `atlantis simulation log` (which would pass `truncate=false`). Requires a deploy to take effect.

- [x] 5. okay. then lets do the following: notice that I have extended the /api/v1/simulations <POST> endpoint and corresponding handler to optionally accept an analysis_options parameter, which exposes the ability to have user-requested analyses run instead of what was previously hardcoded in the actual template itself. N
Now youll see that the user can pass a specification to the request that is explicitly added to the config template, overwriting this value at runtime. Note: if the user doesnt specify it, it uses the default observables. With that said, do the following:
    a0. given all the uncommited work currently (which includes alot of work we have done), please ensure make check passes and then suggest groups of commits in the same way we have been doing interactively, meaning for each commit group, show me the files to stage, the commit message, and a verification description to verify how this change is necessary, t
        then wait for me to tell you to go ahead, and when i do, commit it for me: keep in mind you will need a password for my commiting, which you should then also interactively prompt me for with each commit group.
    a. test and update tests if needed to reflect that change, and actually before you do that, check that any effected code is updated for this ability to have user-specified analysis options (for reference, use the vecoli documentation). Verify that the change works
    b. update all client apps and services (app.cli, app.tui, app.gui, app_data_service) verifiably and tests if needed for this change
    c. update any effected docs/, ./README.md, tutorials, cli-reference in the docs/, any relevant/effected reference if/as needed for this change
    d. ensure make check passes after a, b, and c are verifiabley done
    e. suggest commits in the way we have been doing for all the uncommited work at that point

- [x] 6. the current analysis endpoint (post /api/v1/analyses) is a separate use case for an external user...id like to be able to modularly run analyses on existing simulation output datasets in this example with the 10k simulation workflow run where the       
analyses are taking forever. That particular one is taking forever (and i want it to keep running, still) because i included some extra analysis modules that i didnt need to; thus it would be convient in this case to be able to run a new endpoint called /api/v1/simulations/{id}/analysis with a new cli set of commands oriented (as    
per the existing pattern) around analyses: like atlantis simulation analysis <OPTIONS/PARAMS>. Please do this: implement, test, and verify (add tests if needed), and for reference, have a look at the vecoli documentation readthedocs for the analyses section, as well as this: echo '{"analysis_options": {"experiment_id":               
["sim3-baseline-ca00"], "variant_data_dir": ["/projects/SMS/sms_api/prod/sims/sim3-baseline-ca00/variant_sim_data"], "validation_data_path": ["/projects/SMS/sms_api/prod/sims/sim3-baseline-ca00/parca/kb/validationData.cPickle"], "outdir": "/projects/SMS/sms_api/prod/analyses/analysis-aea4-20260210", "single": {}, "multidaughter":    
{}, "multigeneration": {}, "multiseed": {"ptools_rna": {"n_tp": 22}, "ptools_rxns": {"n_tp": 22}}}, "emitter_arg": {"out_dir": "/projects/SMS/sms_api/prod/sims"}}', which is the expected format for vecoli standalone analyses on existing datasets...thus the new endpoint should use the simulation id passed to look it up in the db, and 
 using the corresponding experiment id, fill out the json config in memory (like as in the workflow, but just without a template, or at least not downloading a template like in that one: use what I just gave as a template.) Youll notice that when putting this config together, the experiment id i sused for certain specific required   
path refs (ie in the example i just gave, variant_data_dir is /projects/SMS/sms_api/prod/sims/sim3-baseline-ca00/variant_sim_data, and the pattern is that its <SIMULATION OUTDIR>/<EXPERIMENT_ID>/variant_sim_data. Cross reference as needed. We want to flex and test this, and make sure we can do it in the cli. Finally ensure make      
check passes and suggest commit groups as we have been doing
- [ ] 11. Task 11 (stream S3 → tar with zero disk cache) is the single refactor that retires pitfalls 2 and 4 from CLAUDE.md at once — whenever you're ready for it
- [ ] 11. Adjust app.cli such that users can do something like: atlantis simulation run help, and it would be equivalent of doing atlantis simulation run --help. Currently, users can only do help on one nesting level above: (ie: atlantis simulation help.)

- [ ] 12. test atlantis cli at scale (10seeds, 10gens) on rke 

- [ ] 13. Ensure cli tests run in CI and set up CI in general

- [ ] 14. Possibly set up CD (robust - PyPI auto)

- [x] 15. I got a feature request for something in the /api/v1/simulation/analyses <POST> endpoint (the one used by ptools). Here are the words I got, lets implement it:
"Hey Alex, we've talked about extending the API so that I can retrieve more customized datasets (e.g. a specific generation, or all generations except the first N, or whatever else users might be interested in)".
"I'm going on vacation next Wednesday, and won't be back until April 30, but these sound like good suggestions. If there is something for me to try out before I go away, or if we should meet to discuss it, I'm happy to do so (I'm free all Thursday morning, Pacific time). Otherwise it will have to wait until I return. But it would be good to have this functionality in place by the time I return, so if there is something I can give input on before then, let me know. My initial thoughts are that you would probably always want a contiguous range of generations, correct? So you might want a single generation, or all between a start (defaulting to 0) and end (defaulting to the last generation) generation, but I can't imagine a situation where you would want a non-contiguous set -- am I wrong? So it might be easier to just specify a start and end generation instead of an array (although that logic can just as easily be handled on the application end if the array makes more sense for you). As for seeds, I would think you would either want a specific single seed or all of them -- under what circumstances might you want a defined subset? And if there are multiple seeds, are there any issues regarding specifying generations? My initial intuition would be that we would just include the specified set of generations from each seed, but since I know that the number of seconds for each generation might differ for the different seeds, I don't know what complications might come up when averaging the data together."

- [ ] 16. Ensure docs are safe (cli quickstart): paths, urls, etc...dont over expose

- [ ] 17. Lets start discussing and drawing up a plan to add auth'd users, or even some token system so any random person cannot ping our hpc willy nilly (rke namespace)

- [ ] 18. Create cover page for PNNL handoff

- [x] 19. Please understand what my coworker (jschaff) has been doing as of most recent on this repo to create a release. We need to hand off a release on main rather than some arbitrary version.
Make note of how its doing.

