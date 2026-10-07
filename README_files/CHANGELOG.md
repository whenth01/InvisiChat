Latest changelog: [Test build V1.0.35](#latest-build)


## Test build V1.0.35 (Development branch)
##### latest build
***THIS IS AN UNSTABLE VERSION, DO NOT USE!***
***THE PREVIOUS VERSION: V1.0.34 (or commit hash c6d1346) IS STABLE, BUT HAS VULNERABILITIES***

***THIS COMMIT WAS MADE EARLY AND FULL DOCUMENTATION FOR THIS CHANGELOG WAS SKIPPED DUE TO MY PHONE(which i use to code on) STORAGE CHIP CAUSING ISSUES AND HAVING SEVERE INSTABILITY***
***SO IM BACKING UP THE CODE***
### Bug fixes
1. Patched a bug where commands could be injected via a modified message shape
2. Added ratelimiting to prevent DoS attacks
3. A bunch of other misc fixes

### Repo changes
1. Added CHANGELOG.md (this one!!:3)
2. Added [ROADMAP.md](ROADMAP.md)
3. Updated [README.md](../README.md) to be linked to the previously mentioned new files

### Code/UI Changes
1. Moved chat button section below contact's username
2. Added remove contact button
3. Added block contact button
4. Removed a long line, unnecessary else and if in chat menu method
5. Reworked the message saver method (add msgs)
  (it was so buggy and messy i cant believe it took me this long to do)
6. Changed the UI in add friends menu