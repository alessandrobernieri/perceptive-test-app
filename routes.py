from flask import render_template, flash, redirect, url_for, request, session, jsonify
from app import app, db
from forms import LoginForm, RegistrationForm, CreateTestForm, TestForm
from models import User, Content, Test, Answer
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
from pathlib import Path
import time, os, os.path, fnmatch, configparser, ast, csv
from collections import defaultdict
from random import seed, randint

@app.route('/')
@app.route('/index')
def index():
    # DA FARE:  risalire a quanti contenuti sono stati svolti e quanti ne mancano
    if not "user_id" in session:
        user=0
        flash('Effettua il log-in vedere i test disponibili.')
        return redirect(url_for('login'))
    test=Test.query.all()
    titoli=list()
    content_available=list()
    test_available=list()
    first_content=list()
    lenghts_total=list()
    lenghts_answered=list()
    for t in test:
        content_available = from_test_to_content_available(t.id)
        if content_available:
            lenghts_total.append(lenght_test(t.id))
            lenghts_answered.append(lenght_answered(t.id))
            if t.type=='img':
                if t.is_double==False:
                    first_content.append(Content.query.filter_by(id=content_available[0]).first())
                if t.is_double==True:
                    first_content.append([Content.query.filter_by(id=content_available[0][0]).first(),Content.query.filter_by(id=content_available[0][1]).first()])
            if t.type=='rank':
                first_content.append([Content.query.filter_by(id=content_available[0][0]).first(),Content.query.filter_by(id=content_available[0][1]).first()])
            if t.type=='video':
                first_content.append('video')
            test_available.append(t)
            titoli.append(from_test_to_title(t.id))
    user = User.query.get(session.get("user_id"))
    return render_template('index.html', title='Home',user=user,test=test_available,titolo=titoli,first=first_content, len_tot=lenghts_total, len_ans=lenghts_answered)

@app.route('/cpadmin')
@login_required
def cpadmin():
    if "user_id" in session:
        user = User.query.get(session.get("user_id"))
        if user.is_admin==True:
            return render_template('cpadmin.html', title="Pannello d' amministrazione", admin=user.is_admin)
        else:
                flash('Non sei abilitato a visualizzare questa pagina.')
                return render_template('cpadmin.html', title='Riservato')

    else:
        flash('Non sei abilitato a visualizzare questa pagina.')
        return render_template('cpadmin.html', title='Riservato')

#RESET

@app.route('/reset_test_eseguiti')
@login_required
def reset_test_eseguiti():
    session['test_done']={}
    flash("reset eseguito")
    return render_template('index.html', title='Home')

#LOGIN, REGISTRAZIONE E LOGOUT USER

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Username o Password non validi.')
            return redirect(url_for('login'))
        # save user information in session
        if not 'test_done' in session:
            session['test_done']={}
        session["user_id"] = user.id
        data = dict(user=dict(id=user.id, username=user.username, email=user.email))
        jsonify(msg="User submitted successfully.", data=data)
        login_user(user, remember=form.remember_me.data)
        # finish save user information in session
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Entra', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, is_admin=False)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulazioni, ti sei appena registrato!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Registrati', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

#INSERIMENTO IMG NEL DB
@app.route('/update_content')
@login_required
def update_content():
    user = User.query.get(session.get("user_id"))
    if user.is_admin==1:
        url_presenti = list()
        img_presenti=Content.query.all()
        for i in range(len(img_presenti)):
            url_presenti.append(img_presenti[i].url)
        directory_img = os.walk("static/content/img/")
        for x in directory_img:
            img_list = os.listdir(x[0])
            for img in img_list:
                if os.path.isdir(os.path.join(x[0],img))==False:
                    path=x[0].replace('static','',1)+'/'+img
                    path=path.replace('//','/')
                    if path not in str(url_presenti):
                        ImgDb=Content(url=path, type="Img")
                        db.session.add(ImgDb)
                        db.session.commit()
                        flash("Aggiunta immagine: "+ImgDb.url)
                    else:
                        flash(path+" già presente")
        directory_video = os.walk("static/content/video/")
        for y in directory_video:
            video_list = os.listdir(y[0])
            for video in video_list:
                if os.path.isdir(os.path.join(y[0],video))==False:
                    path_video=y[0].replace('static','',1)+'/'+video
                    path_video=path_video.replace('//','/')
                    if path_video not in str(url_presenti):
                        ImgDb=Content(url=path_video, type="Video")
                        db.session.add(ImgDb)
                        db.session.commit()
                        flash("Aggiunto video: "+ImgDb.url)
                    else:
                        flash(path+" già presente")
    else:
        flash("Non sei abilitato a questa funzione")
        return redirect(url_for('index'))
    return render_template('index.html', title="Aggiorna gli stimoli")

#CREA - RIMUOVI TEST

@app.route('/create_test', methods=['GET', 'POST'])
@login_required
def create_test():
    user = User.query.get(session.get("user_id"))
    if user.is_admin==1:
        form = CreateTestForm()
        img_presenti = Content.query.filter_by(type="Img").all()
        video_presenti = Content.query.filter_by(type="Video").all()
        if form.validate_on_submit():
            type_content = request.form['type']
            if type_content == 'None':
                flash("Seleziona il tipo di test!")
                return redirect(url_for('create_test'))
            if type_content == 'Img':                           #se test contiene immagini
                subtype_content = request.form['subtype_img']
                if subtype_content == 'None':
                    flash("Seleziona la modalità di test!")
                    return redirect(url_for('create_test'))
                if subtype_content == 'img_single':                     #se test contiene immagini ed è singolo
                    imgsingle = list()
                    if request.files['config-file'].filename == '':
                        for key, val in request.form.items():
                            if key.startswith("imgsingle"):
                                imgsingle.append(val)                               # lista id immagini da inserire nel test singolo
                        if not imgsingle:
                            flash("Seleziona almeno un immagine da inserire nel test!")
                            return redirect(url_for('create_test'))
                    else:
                        config_file=request.files['config-file']
                        for line in config_file.readlines():
                            if check_img_exist(line.rstrip().decode('utf-8'))==False:
                                flash("Un ID non è presente nelle immagini")
                                return redirect(url_for('create_test'))
                            imgsingle.append(line.rstrip().decode('utf-8'))
                    if request.form.get("is_continue")=="continue":             #test singolo accetta valori di rank continui?
                        TestDb=Test(id_img=','.join(imgsingle), type="img", is_continue=1)
                    else:
                        TestDb=Test(id_img=','.join(imgsingle), type="img", is_continue=0)
                    db.session.add(TestDb)
                    db.session.commit()
                    flash("Test creato con successo.")
                if subtype_content == 'img_double':                       #se test contiene immagini ed è doppio
                    imgdouble1 = list()
                    imgdouble2 = list()
                    if request.files['config-file-double'].filename == '':
                        for key, val in request.form.items():
                            if key.startswith("img1double"):
                                imgdouble1.append(val)                          #lista 1 id immagini da inserire nel test doppio
                            if key.startswith("img2double"):
                                imgdouble2.append(val)                          #lista 2 id immagini da inserire nel test doppio
                        if (not imgdouble1) or (not imgdouble2):
                            flash("Seleziona almeno una coppia da inserire nel test!")
                            return redirect(url_for('create_test'))
                    else:
                        config_file=request.files['config-file-double']
                        for line in config_file.readlines():
                            riga=line.rstrip().decode('utf-8').split(',')
                            if (check_img_exist(riga[0])==False) or (check_img_exist(riga[1])==False):
                                flash("Un ID non è presente nelle immagini")
                                return redirect(url_for('create_test'))
                            imgdouble1.append(riga[0])
                            imgdouble2.append(riga[1])
                    if request.form['subtype_double'] == 'double_discreto':
                        TestDb=Test(id_img=','.join(imgdouble1), id_img_double=','.join(imgdouble2), type="img", is_double=1)
                    if request.form['subtype_double'] == 'double_is_continue':
                        TestDb=Test(id_img=','.join(imgdouble1), id_img_double=','.join(imgdouble2), type="img", is_double=1, is_continue=1)
                    if request.form['subtype_double'] == 'double_is_reference':
                        TestDb=Test(id_img=','.join(imgdouble1), id_img_double=','.join(imgdouble2), type="img", is_double=1, is_double_reference=1)                                           #controllo modalità test doppio
                    db.session.add(TestDb)
                    db.session.commit()
                    flash("Test creato con successo.")
                if subtype_content == 'img_rank':                     #se test contiene immagini ed è rank
                    imgrank = list()
                    singleimgrank = list()
                    rank_counter = 1
                    counter = 0
                    if request.files['config-rank'].filename == '':
                        for key,val in request.form.items():
                            if key.startswith("imgrank"+str(rank_counter)+""):
                                counter=counter+1
                                rank_counter=rank_counter+1
                        for i in range(counter):
                            for key, val in request.form.items():
                                if key.startswith("imgrank"+str(i+1)):
                                    singleimgrank.append(val)
                            if len(singleimgrank)<2:
                                flash("Seleziona almeno 2 immagini da inserire nel test!")
                                return redirect(url_for('create_test'))
                            imgrank.append(singleimgrank)
                            singleimgrank = list()
                    else:
                        config_file=request.files['config-rank']
                        for line in config_file.readlines():
                            riga=line.rstrip().decode('utf-8').split(',')
                            for i in riga:
                                if (check_img_exist(i)==False):
                                    flash("Un ID non è presente nelle immagini")
                                    return redirect(url_for('create_test'))
                            if len(riga)<2:
                                flash("Seleziona almeno 2 immagini da inserire nel test!")
                                return redirect(url_for('create_test'))
                            imgrank.append(riga)
                    TestDb=Test(id_img=str(imgrank), type="rank")
                    db.session.add(TestDb)
                    db.session.commit()
                    flash("Test creato con successo.")
            if type_content == 'Video':                           #se test contiene video
                subtype_content = request.form['subtype_video']
                if subtype_content == 'None':
                    flash("Seleziona la modalità di test!")
                    return redirect(url_for('create_test'))
                if subtype_content == 'video_single':                     #se test contiene video ed è singolo
                    videosingle = list()
                    if request.files['config-video'].filename == '':
                        for key, val in request.form.items():
                            if key.startswith("videosingle"):
                                videosingle.append(val)                               # lista id video da inserire nel test singolo
                        if not videosingle:
                            flash("Seleziona almeno un video da inserire nel test!")
                            return redirect(url_for('create_test'))
                    else:
                        config_file=request.files['config-video']
                        for line in config_file.readlines():
                            if check_video_exist(line.rstrip().decode('utf-8'))==False:
                                flash("Un ID non è presente nei video")
                                return redirect(url_for('create_test'))
                            videosingle.append(line.rstrip().decode('utf-8'))
                    if request.form.get("is_continue")=="continue":             #test singolo accetta valori di rank continui?
                        TestDb=Test(id_img=','.join(videosingle), type="video", is_continue=1)
                    else:
                        TestDb=Test(id_img=','.join(videosingle), type="video", is_continue=0)
                    db.session.add(TestDb)
                    db.session.commit()
                    flash("Test creato con successo.")
                if subtype_content == 'video_double':                       #se test contiene video ed è doppio
                    videodouble1 = list()
                    videodouble2 = list()
                    if request.files['config-video-double'].filename == '':
                        for key, val in request.form.items():
                            if key.startswith("video1double"):
                                videodouble1.append(val)                          #lista 1 id video da inserire nel test doppio
                            if key.startswith("video2double"):
                                videodouble2.append(val)                          #lista 2 id video da inserire nel test doppio
                        if (not videodouble1) or (not videodouble2):
                            flash("Seleziona almeno una coppia da inserire nel test!")
                            return redirect(url_for('create_test'))
                    else:
                        config_file=request.files['config-video-double']
                        for line in config_file.readlines():
                            riga=line.rstrip().decode('utf-8').split(',')
                            if (check_video_exist(riga[0])==False) or (check_video_exist(riga[1])==False):
                                flash("Un ID non è presente nei video")
                                return redirect(url_for('create_test'))
                            videodouble1.append(riga[0])
                            videodouble2.append(riga[1])
                    if request.form['subtype_video_double'] == 'double_discreto':
                        TestDb=Test(id_img=','.join(videodouble1), id_img_double=','.join(videodouble2), type="video", is_double=1)
                    if request.form['subtype_video_double'] == 'double_is_continue':
                        TestDb=Test(id_img=','.join(videodouble1), id_img_double=','.join(videodouble2), type="video", is_double=1, is_continue=1)
                    if request.form['subtype_video_double'] == 'double_is_reference':
                        TestDb=Test(id_img=','.join(videodouble1), id_img_double=','.join(videodouble2), type="video", is_double=1, is_double_reference=1)                                           #controllo modalità test doppio
                    db.session.add(TestDb)
                    db.session.commit()
                    flash("Test creato con successo.")
    else:
        flash("Non sei abilitato a questa funzione")
        return redirect(url_for('index'))
    return render_template('create_test.html', title="Crea un test", form=form, img_presenti=img_presenti, video_presenti=video_presenti)

def check_img_exist(id):
    content_presenti = Content.query.filter_by(type="Img").all()
    for i in content_presenti:
        if int(id) == i.id:
            return True
    return False

def check_video_exist(id):
    content_presenti = Content.query.filter_by(type="Video").all()
    for i in content_presenti:
        if int(id) == i.id:
            return True
    return False

@app.route('/remove_test', methods=['GET', 'POST'])
@login_required
def remove_test():
    test = Test.query.all()
    titoli=list()
    for t in test:
        titoli.append(from_test_to_title(t.id))
    form = TestForm()
    if form.validate_on_submit():
        id_test_delete = request.form['test']
        test_delete = Test.query.filter_by(id=id_test_delete).first()
        db.session.delete(test_delete)
        db.session.commit()
        flash("Test rimosso con successo.")
        return redirect(url_for('remove_test'))
    return render_template('remove_test.html', title='Rimuovi  un test', form=form, test_presenti=test, titoli=titoli)

#VISUALIZZAZIONE TEST

@app.route('/test/<int:id>', methods=['GET', 'POST'])
@login_required
def test(id):
    this_test = Test.query.filter_by(id=id).first()
    id_quoted = ''+str(id)+''
    if not 'test_done' in session:
        session['test_done'] = {}
    if not id_quoted in session['test_done']:
        session['test_done'][id_quoted] = list()
    form = TestForm()
    content = from_test_to_content_available(id) #ritorna lista id content disponibili, togliendo i test già fatti
    if not content:
        flash("Test completato.")
        return redirect(url_for('index'))
    nrtest = lenght_test(id)
    nrnow = nrtest - len(content) +1
    this_title=from_test_to_title(id)
    this_description=from_test_to_description(id)
    time_grayscreen=timing()
    if this_title:
        titolo=this_title
    else:
        titolo='Test id '+str(id)
    if this_test.type=='rank':
        urls = list()
        list_img = list()
        random=randint(0,len(content)-1)
        try:
            this_content=ast.literal_eval(content[random])
        except IndexError:
            flash("Test completato.")
            return redirect(url_for('index'))
        for i in this_content:
            urls.append((Content.query.filter_by(id=i).first()).url)
            list_img.append((Content.query.filter_by(id=i).first()).id)
        if request.method == 'POST':
            session['test_done'][id_quoted].append(eval(request.form['test']))
            listcontent=request.form['single_img']
            listcontent=listcontent.replace(']','')
            listcontent=listcontent.replace('[','')
            listcontent=listcontent.replace(' ','')
            answer=Answer(id_test=id, list_img=listcontent, list_rank=request.form['result'])
            db.session.add(answer)
            db.session.commit()
            flash("Risposta inserita correttamente.")
            return redirect(url_for('test', id=id))
        return render_template('test.html', title=titolo, this_title=this_title, this_description=this_description, content=this_content, form=form, urls = urls, lenght = len(list_img), test = this_test, contents = list_img, id=id, type=this_test.type, nrnow=nrnow, nrtest=nrtest, time_grayscreen=time_grayscreen)
    else:
        if this_test.is_double==True:
            if this_test.is_double_reference==True:
                this_test_choices = from_test_to_choices(id)
            else:
                this_test_choices = from_double_test_to_choices(id)
            random=randint(0,len(content)-1)
            double_content=content[random]
            single1_content=double_content[0]
            single2_content=double_content[1]
            this_content1 = Content.query.filter_by(id=single1_content).first()
            this_content2 = Content.query.filter_by(id=single2_content).first()
            if form.validate_on_submit():
                session['test_done'][id_quoted].append(eval(request.form['test']))
                if this_test.is_double_reference==True:
                    if not 'choices' in request.form:
                        reason1='none'
                    else:
                        reason1=request.form['choices']
                    answer=Answer(id_test=id, id_img1=request.form['test1'], id_img2=request.form['test2'], choice=request.form['videodouble'], reason1=reason1)
                else:
                    if not 'choices1' in request.form:
                        reason1='none'
                    else:
                        reason1=request.form['choices1']
                    if not 'choices2' in request.form:
                        reason2='none'
                    else:
                        reason2=request.form['choices2']
                    answer=Answer(id_test=id, id_img1=request.form['test1'], id_img2=request.form['test2'], rating1=request.form['voto1'], rating2=request.form['voto2'], reason1=reason1, reason2=reason2)
                db.session.add(answer)
                db.session.commit()
                flash("Risposta inserita correttamente.")
                return redirect(url_for('test', id=id))
            return render_template('test.html', title=titolo, this_title=this_title, this_description=this_description, form=form, content=double_content, content1 = this_content1, content2 = this_content2, id=id, type=this_test.type, is_double=this_test.is_double, is_double_reference=this_test.is_double_reference, is_continue = this_test.is_continue, nrtest=nrtest, nrnow=nrnow, choices=this_test_choices, time_grayscreen=time_grayscreen)
        elif this_test.is_double==False:
            this_test_choices = from_test_to_choices(id)
            random=randint(0,len(content)-1)
            single_content=content[random]
            this_content = Content.query.filter_by(id=single_content).first()
            if form.validate_on_submit():
                session['test_done'][id_quoted].append(request.form['test'])
                if not 'choices' in request.form:
                    answer=Answer(id_test=id, id_img1=request.form['test'], rating1=request.form['voto'], reason1='none')
                else:
                    answer=Answer(id_test=id, id_img1=request.form['test'], rating1=request.form['voto'], reason1=request.form['choices'])
                db.session.add(answer)
                db.session.commit()
                flash("Risposta inserita correttamente.")
                return redirect(url_for('test', id=id))
            return render_template('test.html', title=titolo, form=form, this_title=this_title, this_description=this_description, content = this_content, id=id, type=this_test.type, is_double=this_test.is_double, is_continue = this_test.is_continue, nrtest=nrtest, nrnow=nrnow, choices=this_test_choices, time_grayscreen=time_grayscreen)

def from_test_to_content_available(id):
    id_quoted = ''+str(id)+''
    if not id_quoted in session['test_done']:
        session['test_done'][id_quoted] = list()
    test = Test.query.filter_by(id=id).first()
    content_available=list()
    if not test:
        return content_available
    if(test.type=='rank'):
        content_in_test=test.id_img
        content_in_test=ast.literal_eval(content_in_test)
        content_done = session.get("test_done")[''+str(id)+'']
        if content_done is None:
            content_done = list()
        for i in range(len(content_in_test)):
            check = str(content_in_test[i])
            if eval(check) not in content_done:
                content_available.append(check)
        return content_available
    if(test.is_double==True):
        content_in_test=list()
        content1_in_test=test.id_img.split(",")
        content2_in_test=test.id_img_double.split(",")
        for x in range(len(content1_in_test)):
            content_in_test.append([content1_in_test[x],content2_in_test[x]])
        content_done = session.get("test_done")[''+str(id)+'']
        if content_done is None:
            content_done = list ()
        for i in range(len(content_in_test)):
            check = str(content_in_test[i])
            check = eval(check)
            if check not in content_done:
                content_available.append(check)
    else:
        content_in_test=test.id_img.split(",")
        content_done = session.get("test_done")[''+str(id)+'']
        if content_done is None:
            content_done = list()
        for i in range(len(content_in_test)):
            check = str(content_in_test[i])
            if check not in content_done:
                content_available.append(check)
    return content_available

def lenght_test(id):
    counter = 0
    test = Test.query.filter_by(id=id).first()
    if test.type=='rank':
        test = Test.query.filter_by(id=id).first()
        content_in_test=test.id_img
        content_in_test=ast.literal_eval(content_in_test)
        return len(content_in_test)
    content_in_test=test.id_img.split(",")
    for i in range(len(content_in_test)):
        counter+=1
    return counter

def lenght_answered(id):
    counter = 0
    id_quoted = ''+str(id)+''
    if not id_quoted in session['test_done']:
        return counter
    else:
        for i in session['test_done'][id_quoted]:
            counter=counter+1
    return counter


#REASON E FILE CONFIG

@app.route('/changechoices', methods=['GET', 'POST'])
@login_required
def changechoices():
    form = TestForm()
    test=Test.query.all()
    titoli=list()
    for t in test:
        titoli.append(from_test_to_title(t.id))
    if form.validate_on_submit():
        id_test=request.form['test']
        return redirect(url_for('change_choices',id=id_test))
    return render_template('change_choices_home.html', title='Modifica le opzioni', form=form, test_presenti=test, titoli=titoli)

@app.route('/change_choices/<int:id>', methods=['GET', 'POST'])
@login_required
def change_choices(id):
    form=TestForm()
    test=Test.query.filter_by(id=id).first()
    if test is None:
        flash('Non puoi modificare le opzioni relative a un test non esistente.')
        return redirect(url_for('index'))
    if test.type=='rank':
        flash('Non puoi modificare le opzioni relative a un test Classifica')
        return redirect(url_for('index'))
    choices_old=test_to_choices(id=id)
    if form.validate_on_submit():
        config = configparser.RawConfigParser()
        config.read('config.txt')
        if test.is_double==False or test.is_double_reference==True:
            choices_new = list()
            for key,val in request.form.items():
                if key.startswith("choices"):
                    choices_new.append(val)
            choices_new_string = ','.join(choices_new)
        if test.is_double==True and test.is_double_reference==False:
            choices1_new = list()
            choices2_new = list()
            for key,val in request.form.items():
                if key.startswith("choices1_"):
                    choices1_new.append(val)
                if key.startswith("choices2_"):
                    choices2_new.append(val)
            choices1_new_string = ','.join(choices1_new)
            choices2_new_string = ','.join(choices2_new)
            choices_new_string = choices1_new_string+'-'+choices2_new_string
        config.remove_option('choice_config', str(id))
        if choices_new_string:
            config.set('choice_config', str(id), choices_new_string)
        with open("config.txt", "w") as f:
            config.write(f)
        flash("Opzioni modificate con successo.")
        return redirect(url_for('change_choices', id=id))
    return render_template('change_choices.html', title='Modifica le opzioni', test=test, form=form, id=id, choices_old=choices_old)

def test_to_choices(id):
    this_test = Test.query.filter_by(id=id).first()
    if this_test.type=='rank':
        return []
    if this_test.is_double==True:
        if this_test.is_double_reference==False:
            x = from_double_test_to_choices(id)
            return x
        else:
            x = from_test_to_choices(id)
            return x
    else:
        x = from_test_to_choices(id)
        return x

def from_test_to_choices(id):
    config = configparser.RawConfigParser()
    config.read('config.txt')
    choices = dict(config.items('choice_config'))
    if not ''+str(id)+'' in choices:
        options=list()
        return options
    options = choices[''+str(id)+''].split(',')
    return options

def from_double_test_to_choices(id):
    config = configparser.RawConfigParser()
    config.read('config.txt')
    choices = dict(config.items('choice_config'))
    if not ''+str(id)+'' in choices:
        options=list()
        return options
    options = choices[''+str(id)+''].split('-')
    content_choices = list()
    for i in range(len(options)):
        content_choices.append(options[i].split(','))
    return content_choices

#TITOLO & DESCRIZIONE TEST

@app.route('/changetitle', methods=['GET', 'POST'])
@login_required
def changetitle():
    form = TestForm()
    test=Test.query.all()
    titoli=list()
    for t in test:
        titoli.append(from_test_to_title(t.id))
    if form.validate_on_submit():
        id_test=request.form['test']
        return redirect(url_for('change_title',id=id_test))
    return render_template('change_title_home.html', title='Modifica il titolo', form=form, test_presenti=test, titoli=titoli)

@app.route('/change_title/<int:id>', methods=['GET', 'POST'])
@login_required
def change_title(id):
    form=TestForm()
    test=Test.query.filter_by(id=id).first()
    if test is None:
        flash('Non puoi modificare il titolo relativo a un test non esistente.')
        return redirect(url_for('changetitle'))
    title_old=from_test_to_title(id)
    if form.validate_on_submit():
        config = configparser.RawConfigParser()
        config.read('config.txt')
        title_new=''
        for key,val in request.form.items():
                if key.startswith("title"):
                    title_new=val
        config.remove_option('title_config', str(id))
        if title_new:
            config.set('title_config', str(id), title_new)
        with open("config.txt", "w") as f:
            config.write(f)
        flash("Titolo modificato con successo.")
        return redirect(url_for('change_title', id=id))
    return render_template('change_title.html', title='Modifica il titolo', test=test, form=form, id=id, title_old=title_old)

def from_test_to_title(id):
    config = configparser.RawConfigParser()
    config.read('config.txt')
    title = dict(config.items('title_config'))
    if not ''+str(id)+'' in title:
        this_title=None
        return this_title
    this_title = title[''+str(id)+'']
    return this_title

@app.route('/changedescription', methods=['GET', 'POST'])
@login_required
def changedescription():
    form = TestForm()
    test=Test.query.all()
    titoli=list()
    for t in test:
        titoli.append(from_test_to_title(t.id))
    if form.validate_on_submit():
        id_test=request.form['test']
        return redirect(url_for('change_description',id=id_test))
    return render_template('change_description_home.html', title='Modifica la descrizione', form=form, test_presenti=test, titoli=titoli)

@app.route('/change_description/<int:id>', methods=['GET', 'POST'])
@login_required
def change_description(id):
    form=TestForm()
    test=Test.query.filter_by(id=id).first()
    if test is None:
        flash('Non puoi modificare la descrizione relativa a un test non esistente.')
        return redirect(url_for('changedescription'))
    description_old=from_test_to_description(id)
    if form.validate_on_submit():
        config = configparser.RawConfigParser()
        config.read('config.txt')
        description_new=''
        for key,val in request.form.items():
                if key.startswith("description"):
                    description_new=val
        config.remove_option('description_config', str(id))
        if description_new:
            config.set('description_config', str(id), description_new)
        with open("config.txt", "w") as f:
            config.write(f)
        flash("Descrizione modificata con successo.")
        return redirect(url_for('change_description', id=id))
    return render_template('change_description.html', title='Modifica la descrizione', test=test, form=form, id=id, description_old=description_old)

def from_test_to_description(id):
    config = configparser.RawConfigParser()
    config.read('config.txt')
    description = dict(config.items('description_config'))
    if not ''+str(id)+'' in description:
        this_description=None
        return this_description
    this_description = description[''+str(id)+'']
    return this_description

#STATISTICHE

@app.route('/stats', methods=['GET', 'POST'])
@login_required
def stats():
    form=TestForm()
    tests=Test.query.all()
    titoli=list()
    for t in tests:
        titoli.append(from_test_to_title(t.id))
    if form.validate_on_submit():
        if request.form['test']=='None':
            flash('Seleziona un test')
        else:
            return redirect(url_for('test_stats',id=request.form['test']))
    return render_template('stats.html',title='Statistiche',form=form,test_presenti=tests,titoli=titoli)

@app.route('/test_stats/<int:id>', methods=['GET', 'POST'])
@login_required
def test_stats(id):
    this_test=Test.query.filter_by(id=id).first()
    form=TestForm()
    if form.validate_on_submit():
        result=stats_to_csv(id)
        return redirect("../static/stats/stats_"+str(id)+".csv", code=302)
    if this_test is None:
        flash("Non esiste alcun test con questo ID")
        return redirect(url_for('index'))
    if this_test.is_double==False:
        if this_test.type=='rank':
            test_stats=test_stats_rank(id)
            return render_template('test_stats.html',title='Statistiche',form=form,test=this_test,contents=test_stats[0],stats=test_stats[1])
        else:
            return render_template('test_stats.html',title='Statistiche',form=form,test=this_test,contents=test_stats_single(id)[0],stats=test_stats_single(id)[1],choices=test_stats_single(id)[2],choices_count=test_stats_single(id)[3])
    else:
        if this_test.is_double_reference==True:
            return render_template('test_stats.html',title='Statistiche',form=form,test=this_test,contents1=test_stats_double_reference(id)[0],stats=test_stats_double_reference(id)[2],contents2=test_stats_double_reference(id)[1],choices=test_stats_double_reference(id)[3],choices_count=test_stats_double_reference(id)[4])
        else:
            return render_template('test_stats.html',title='Statistiche',form=form,test=this_test,contents1=test_stats_double(id)[0],stats=test_stats_double(id)[2],contents2=test_stats_double(id)[1],choices=test_stats_double(id)[3],choices_count1=test_stats_double(id)[4],choices_count2=test_stats_double(id)[5])

def test_stats_single(id):
        this_test=Test.query.filter_by(id=id).first()
        contents=list()
        content_stats_list=list()
        content_choices_list=list()
        content_list=(this_test.id_img).split(',')
        choices=from_test_to_choices(id)
        for i in content_list:
            contents.append(Content.query.filter_by(id=i).first())
            content_stats_list.append(from_single_test_to_stats(i,id))
            content_choices_list.append(from_single_test_to_choices(i,id,choices))
        return contents, content_stats_list, choices, content_choices_list

def test_stats_rank(id):
    this_test=Test.query.filter_by(id=id).first()
    single_contents=list()
    contents=list()
    content_stats_list=list()
    content_list=ast.literal_eval(this_test.id_img)
    for i in content_list:
        for z in i:
            single_contents.append(Content.query.filter_by(id=z).first())
        content_stats_list.append(from_rank_test_to_stats(i,id))
        contents.append(single_contents)
        single_contents=list()
    return contents, content_stats_list

def test_stats_double_reference(id):
        this_test=Test.query.filter_by(id=id).first()
        contents1=list()
        contents2=list()
        content_stats_list=list()
        content_choices_list=list()
        content_list1=(this_test.id_img).split(',')
        content_list2=(this_test.id_img_double).split(',')
        choices=from_test_to_choices(id)
        for i in range(len(content_list1)):
            contents1.append(Content.query.filter_by(id=content_list1[i]).first())
            contents2.append(Content.query.filter_by(id=content_list2[i]).first())
            content_stats_list.append(from_reference_test_to_stats(content_list1[i],content_list2[i],id))
            content_choices_list.append(from_reference_test_to_choices(content_list1[i],content_list2[i],id,choices))
        return contents1,contents2,content_stats_list,choices,content_choices_list

def test_stats_double(id):
    this_test=Test.query.filter_by(id=id).first()
    contents1=list()
    contents2=list()
    content_stats_list=list()
    content_choices_list1=list()
    content_choices_list2=list()
    content_list1=(this_test.id_img).split(',')
    content_list2=(this_test.id_img_double).split(',')
    choices=from_double_test_to_choices(id)
    for i in range(len(content_list1)):
        contents1.append(Content.query.filter_by(id=content_list1[i]).first())
        contents2.append(Content.query.filter_by(id=content_list2[i]).first())
        content_stats_list.append(from_double_test_to_stats(content_list1[i],content_list2[i],id))
        content_choices_list1.append(from_doublee_test_to_choices(content_list1[i],content_list2[i],id,choices)[0])
        content_choices_list2.append(from_doublee_test_to_choices(content_list1[i],content_list2[i],id,choices)[1])
    return contents1,contents2,content_stats_list,choices,content_choices_list1,content_choices_list2

def from_single_test_to_stats(id_content,id_test):
    answers=Answer.query.filter_by(id_img1=id_content,id_img2=None,id_test=id_test).all()
    nrvoti=0
    somma=0
    media=0
    if not answers:
        return nrvoti,media
    for i in answers:
        nrvoti=nrvoti+1
        somma=somma+i.rating1
    media=somma/nrvoti
    return nrvoti,round(media,2)

def from_rank_test_to_stats(id_content,id_test):
    answers=Answer.query.filter_by(id_test=id_test,list_img=','.join(id_content)).all()
    list_rank=list()
    for x in answers:
        list_rank.append((x.list_rank).split(','))
    somma=0
    media=0
    nrvoti=0
    somma_list=list()
    media_list=list()
    for k in list_rank:
        nrvoti=nrvoti+1
    for i in id_content:
        for y in list_rank:
            for z in range(len(y)):
                if i==y[z]:
                    somma=somma+(z+1)
        somma_list.append(somma)
        somma=0
    for s in somma_list:
        if nrvoti==0:
            media=0
        else:
            media=s/nrvoti
            media=round(media,2)
        media_list.append(media)
        media=0
    return nrvoti,media_list

def from_reference_test_to_stats(id_content1,id_content2,id_test):
    answers=Answer.query.filter_by(id_img1=id_content1,id_img2=id_content2,id_test=id_test).all()
    counter1=0
    counter2=0
    if not answers:
        return counter1,counter2
    for i in answers:
        if i.choice==int(id_content1):
            counter1=counter1+1
        if i.choice==int(id_content2):
            counter2=counter2+1
    return counter1,counter2

def from_double_test_to_stats(id_content1,id_content2,id_test):
    answers=Answer.query.filter_by(id_img1=id_content1,id_img2=id_content2,id_test=id_test).all()
    nrvoti1=0
    somma1=0
    media1=0
    nrvoti2=0
    somma2=0
    media2=0
    if not answers:
        return nrvoti1,media1,nrvoti2,media2
    for i in answers:
        nrvoti1=nrvoti1+1
        somma1=somma1+i.rating1
        nrvoti2=nrvoti2+1
        somma2=somma2+i.rating2
    media1=somma1/nrvoti1
    media2=somma2/nrvoti2
    return nrvoti1,round(media1,2),nrvoti2,round(media2,2)

def from_single_test_to_choices(id_content,id_test,choices):
    choices_count=list()
    for i in choices:
        choices_count.append(Answer.query.filter_by(id_img1=id_content,id_img2=None,id_test=id_test,reason1=i).count())
    return choices_count

def from_reference_test_to_choices(id_content1,id_content2,id_test,choices):
    choices_count=list()
    for i in choices:
        choices_count.append(Answer.query.filter_by(id_img1=id_content1,id_img2=id_content2,id_test=id_test,reason1=i).count())
    return choices_count

def from_doublee_test_to_choices(id_content1,id_content2,id_test,choices):
    choices_count1=list()
    choices_count2=list()
    try:
        for i in choices[0]:
            choices_count1.append(Answer.query.filter_by(id_img1=id_content1,id_img2=id_content2,id_test=id_test,reason1=i).count())
    except IndexError:
        choices_count1=list()
    try:
        for i in choices[1]:
            choices_count2.append(Answer.query.filter_by(id_img1=id_content1,id_img2=id_content2,id_test=id_test,reason2=i).count())
    except IndexError:
        return choices_count1,choices_count2
    return choices_count1,choices_count2

def stats_to_csv(id):
    this_test=Test.query.filter_by(id=id).first()
    if this_test is None:
        flash("Non esiste alcun test con questo ID")
        return redirect(url_for('index'))
    if this_test.is_double==False:
        if this_test.type=='rank':                                                  # SE RANK
            test_stats=test_stats_rank(id)
            with open('static/stats/stats_'+str(id)+'.csv', mode='w', newline='') as stats_file:
                stats_writer=csv.writer(stats_file, delimiter=',', quoting=csv.QUOTE_MINIMAL, dialect='excel')
                header = ['STEP','ID CONTENT','URL','VOTI','POSIZIONE MEDIA']
                stats_writer.writerow(x for x in header)
                single = list()
                for i in range(len(test_stats[0])):
                    for y in range(len(test_stats[0][i])):
                        single.append(i+1)
                        this_content=Content.query.filter_by(id=str(test_stats[0][i][y])).first()
                        single.append(this_content.id)
                        single.append(this_content.url)
                        single.append(test_stats[1][i][0])
                        single.append(test_stats[1][i][1][y])
                        stats_writer.writerow(y for y in single)
                        single = list()
        else:                                                                       # SE SINGOLO
            test_stats=test_stats_single(id)
            with open('static/stats/stats_'+str(id)+'.csv', mode='w', newline='') as stats_file:
                stats_writer=csv.writer(stats_file, delimiter=',', quoting=csv.QUOTE_MINIMAL, dialect='excel')
                header = ['ID CONTENT','URL','VOTI','MEDIA VOTI']
                for i in test_stats[2]:
                    header.append(i)
                stats_writer.writerow(x for x in header)
                single = list()
                for i in range(len(test_stats[0])):
                    this_content=Content.query.filter_by(id=str(test_stats[0][i])).first()
                    single.append(this_content.id)
                    single.append(this_content.url)
                    single.append(test_stats[1][i][0])
                    single.append(test_stats[1][i][1])
                    for y in range(len(test_stats[2])):
                        single.append(test_stats[3][i][y])
                    stats_writer.writerow(y for y in single)
                    single = list()
    else:
        if this_test.is_double_reference==True:                                     # SE DOPPIO REFERENCE
            test_stats=test_stats_double_reference(id)
            with open('static/stats/stats_'+str(id)+'.csv', mode='w', newline='') as stats_file:
                stats_writer=csv.writer(stats_file, delimiter=',', quoting=csv.QUOTE_MINIMAL, dialect='excel')
                header = ['STEP','ID #1','VOTI #1','ID #2','VOTI #2','URL #1','URL #2']
                for i in range(len(test_stats[3])):
                    header.append(test_stats[3][i])
                stats_writer.writerow(x for x in header)
                single = list()
                for k in range(len(test_stats[0])):
                    single.append(k+1)
                    this_content1=Content.query.filter_by(id=str(test_stats[0][k])).first()
                    this_content2=Content.query.filter_by(id=str(test_stats[1][k])).first()
                    single.append(this_content1.id)
                    single.append(test_stats[2][k][0])
                    single.append(this_content2.id)
                    single.append(test_stats[2][k][1])
                    single.append(this_content1.url)
                    single.append(this_content2.url)
                    for z in range(len(test_stats[3])):
                        single.append(test_stats[4][k][z])
                    stats_writer.writerow(v for v in single)
                    single = list()
        else:                                                                       # SE DOPPIO
            test_stats=test_stats_double(id)
            with open('static/stats/stats_'+str(id)+'.csv', mode='w', newline='') as stats_file:
                stats_writer=csv.writer(stats_file, delimiter=',', quoting=csv.QUOTE_MINIMAL, dialect='excel')
                header = ['STEP','VOTI','ID #1','VOTO #1','ID #2','VOTO #2','URL #1','URL #2']
                for i in range(len(test_stats[3])):
                    for y in range(len(test_stats[3][i])):
                        header.append(test_stats[3][i][y]+' #'+str(i+1))
                stats_writer.writerow(x for x in header)
                single = list()
                for k in range(len(test_stats[0])):
                    single.append(k+1)
                    single.append(test_stats[2][k][0])
                    this_content1=Content.query.filter_by(id=str(test_stats[0][k])).first()
                    this_content2=Content.query.filter_by(id=str(test_stats[1][k])).first()
                    single.append(this_content1.id)
                    single.append(test_stats[2][k][1])
                    single.append(this_content2.id)
                    single.append(test_stats[2][k][3])
                    single.append(this_content1.url)
                    single.append(this_content2.url)
                    for z in range(len(test_stats[4][k])):
                        single.append(test_stats[4][k][z])
                    for h in range(len(test_stats[5][k])):
                        single.append(test_stats[5][k][h])
                    stats_writer.writerow(v for v in single)
                    single = list()
    return 1

# ISTRUZIONI, CALIBRAZIONE

@app.route('/istruzioni/<int:id>', methods=['GET', 'POST'])
@login_required
def istruzioni(id):
    form = TestForm()
    instruction=from_test_to_instruction(id)
    if not instruction:
        return redirect(url_for('calibrazione', id=id))
    if form.validate_on_submit():
        return redirect(url_for('calibrazione', id=id))
    return render_template('istruzioni.html', title='Istruzioni', form=form, instruction=instruction)

@app.route('/changeinstruction', methods=['GET', 'POST'])
@login_required
def changeinstruction():
    form = TestForm()
    titoli=list()
    test=Test.query.all()
    for t in test:
        titoli.append(from_test_to_title(t.id))
    if form.validate_on_submit():
        id_test=request.form['test']
        return redirect(url_for('change_instruction',id=id_test))
    return render_template('change_instruction_home.html', title='Modifica le istruzioni', form=form, test_presenti=test, titoli=titoli)

@app.route('/change_instruction/<int:id>', methods=['GET', 'POST'])
@login_required
def change_instruction(id):
    form=TestForm()
    test=Test.query.filter_by(id=id).first()
    if test is None:
        flash('Non puoi modificare le istruzioni relative a un test non esistente.')
        return redirect(url_for('changeinstruction'))
    instruction_old=from_test_to_instruction(id)
    if form.validate_on_submit():
        config = configparser.RawConfigParser()
        config.read('config_instruction.txt')
        instruction_new=''
        for key,val in request.form.items():
                if key.startswith("instruction"):
                    instruction_new=val
        config.remove_option('instruction_config', str(id))
        if instruction_new:
            config.set('instruction_config', str(id), instruction_new)
        with open("config_instruction.txt", "w") as f:
            config.write(f)
        flash("Istruzioni modificate con successo.")
        return redirect(url_for('change_instruction', id=id))
    return render_template('change_instruction.html', title='Modifica le istruzioni', test=test, form=form, id=id, instruction_old=instruction_old)

def from_test_to_instruction(id):
    config = configparser.RawConfigParser()
    config.read('config_instruction.txt')
    instruction = dict(config.items('instruction_config'))
    if not ''+str(id)+'' in instruction:
        this_instruction=None
        return this_instruction
    this_instruction = instruction[''+str(id)+'']
    return this_instruction

@app.route('/calibrazione/<int:id>', methods=['GET', 'POST'])
@login_required
def calibrazione(id):
    form = TestForm()
    if form.validate_on_submit():
        return redirect(url_for('test', id=id))
    return render_template('calibrazione.html', title='Calibrazione Luminosità/Contrasto', form=form)

# GRAY SCREEN & TIMING

def timing():
    config = configparser.RawConfigParser()
    config.read('config.txt')
    general = dict(config.items('general'))
    if not 'time_grayscreen' in general:
        time=0              # di default è 0(s) (disattivato)
        return time
    time = general['time_grayscreen']
    return time

@app.route('/change_time', methods=['GET', 'POST'])
@login_required
def change_time():
    form=TestForm()
    time=timing()
    if form.validate_on_submit():
        config = configparser.RawConfigParser()
        config.read('config.txt')
        time_new=''
        for key,val in request.form.items():
                if key.startswith("time"):
                    time_new=val
        if time_new:
            config.remove_option('general', 'time_grayscreen')
            config.set('general', 'time_grayscreen', time_new)
        with open("config.txt", "w") as f:
            config.write(f)
        flash("Tempo gray-screen modificato con successo.")
        return redirect(url_for('change_time'))
    return render_template('change_time.html', title='Modifica duranta di gray-screen', test=test, form=form, id=id, time_old=time)