rem cmd /C compile
rem copy app.yaml app.yaml.tmp
rem grep -v NOTPROD app.yaml.tmp > app.yaml
rem type app.yaml
python -u "C:\Program Files (x86)\Google\google_appengine\appcfg.py" -A gmailtimer-1264 --email=adelespinasse@gmail.com update .
rem del app.yaml
rem ren app.yaml.tmp app.yaml