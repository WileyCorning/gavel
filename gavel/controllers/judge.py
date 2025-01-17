from gavel import app
from gavel.models import *
from gavel.constants import *
import gavel.settings as settings
import gavel.utils as utils
import gavel.crowd_bt as crowd_bt
from sqlalchemy import and_,or_,not_
from flask import (
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from numpy.random import choice, random, shuffle
from functools import wraps
from datetime import datetime

def requires_open(redirect_to):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if Setting.value_of(SETTING_CLOSED) == SETTING_TRUE:
                return redirect(url_for(redirect_to))
            else:
                return f(*args, **kwargs)
        return decorated
    return decorator

def requires_active_annotator(redirect_to):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            annotator = get_current_annotator()
            if annotator is None or not annotator.active:
                return redirect(url_for(redirect_to))
            else:
                return f(*args, **kwargs)
        return decorated
    return decorator


@app.route('/')
def index():
    annotator = get_current_annotator()
    if annotator is None:
        return render_template(
            'logged_out.html',
            content=utils.render_markdown(settings.LOGGED_OUT_MESSAGE)
        )
    else:
        if Setting.value_of(SETTING_CLOSED) == SETTING_TRUE:
            return render_template(
                'closed.html',
                content=utils.render_markdown(settings.CLOSED_MESSAGE)
            )
        if not annotator.active:
            return render_template(
                'disabled.html',
                content=utils.render_markdown(settings.DISABLED_MESSAGE)
            )
        if not annotator.read_welcome:
            return redirect(url_for('welcome'))
        maybe_init_annotator()
        zone_options = get_distinct_zones()
        if annotator.next is None:  
            return render_template(
                'wait.html',
                ignored=[ig.name for ig in annotator.ignore],
                viewed=[v.name for v in annotator.viewed],
                content=utils.render_markdown(settings.WAIT_MESSAGE),
                zone=annotator.zone, zone_options=zone_options
            )
        elif annotator.prev is None:
            return render_template('begin.html', item=annotator.next, zone=annotator.zone, zone_options=zone_options)
        else:
            prev_viewed = annotator in annotator.prev.viewed
            next_viewed = annotator in annotator.next.viewed
            print(prev_viewed)
            print(next_viewed)
            return render_template('vote.html', prev=annotator.prev,prev_viewed=prev_viewed,next=annotator.next,next_viewed=next_viewed, zone=annotator.zone, zone_options=zone_options)

def get_distinct_zones():
    return [z[0] for z in Item.query.with_entities(Item.zone).distinct()]

@app.route('/set_zone',methods=['POST'])
@requires_open(redirect_to='index')
@requires_active_annotator(redirect_to='index')
def set_zone():
    def tx():
        annotator = get_current_annotator()
        annotator.zone = request.form['next-zone']
        print(annotator.zone)
    
        if(annotator.next is None or (
            # Shuffle next if (a) it's fresh and we're moving to a different zone, or (b) it's reheated and we're reentering its zone
            (annotator in annotator.next.viewed and annotator.next.zone == annotator.zone) or
            (annotator not in annotator.next.viewed and annotator.next.zone != annotator.zone)
        )):
            annotator.update_next(choose_next(annotator))
        
        db.session.commit()
    with_retries(tx)
    return redirect(url_for('index'))

@app.route('/vote', methods=['POST'])
@requires_open(redirect_to='index')
@requires_active_annotator(redirect_to='index')
def vote():
    def tx():
        annotator = get_current_annotator()
        if annotator.prev.id == int(request.form['prev_id']) and annotator.next.id == int(request.form['next_id']):
            if request.form['action'] == 'Skip':
                annotator.ignore.append(annotator.next)
            else:
                # ignore things that were deactivated in the middle of judging
                if annotator.prev.active and annotator.next.active:
                    if request.form['action'] == 'Previous':
                        perform_vote(annotator, next_won=False)
                        decision = Decision(annotator, winner=annotator.prev, loser=annotator.next)
                    elif request.form['action'] == 'Current':
                        perform_vote(annotator, next_won=True)
                        decision = Decision(annotator, winner=annotator.next, loser=annotator.prev)
                    db.session.add(decision)
                '''
                [Wiley] Adjustment note

                The original Gavel logic ignores an item as soon as it is voted.

                Here, we change this so that the item will only be ignored if this is its *second* vote.

                The effect is that an item can reappear once the annotator is in a different zone.
                See changes made to the selection logic.
                '''
                # Check if this `next` is resurfacing
                was_previously_viewed = annotator in annotator.next.viewed
                
                if was_previously_viewed:
                    annotator.ignore.append(annotator.next)
                else:
                    annotator.next.viewed.append(annotator) # counted as viewed even if deactivated
                    annotator.prev = annotator.next
            
            annotator.update_next(choose_next(annotator))
            db.session.commit()
    with_retries(tx)
    return redirect(url_for('index'))

@app.route('/begin', methods=['POST'])
@requires_open(redirect_to='index')
@requires_active_annotator(redirect_to='index')
def begin():
    def tx():
        annotator = get_current_annotator()
        if annotator.next.id == int(request.form['item_id']):
            annotator.ignore.append(annotator.next)
            if request.form['action'] == 'Continue':
                annotator.next.viewed.append(annotator)
                annotator.prev = annotator.next
                annotator.update_next(choose_next(annotator))
            elif request.form['action'] == 'Skip':
                annotator.next = None # will be reset in index
            db.session.commit()
    with_retries(tx)
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop(ANNOTATOR_ID, None)
    return redirect(url_for('index'))

@app.route('/login/<secret>/')
def login(secret):
    annotator = Annotator.by_secret(secret)
    if annotator is None:
        session.pop(ANNOTATOR_ID, None)
        session.modified = True
    else:
        session[ANNOTATOR_ID] = annotator.id
    return redirect(url_for('index'))

@app.route('/welcome/')
@requires_open(redirect_to='index')
@requires_active_annotator(redirect_to='index')
def welcome():
    zone_options = get_distinct_zones()
    return render_template(
        'welcome.html',
        content=utils.render_markdown(settings.WELCOME_MESSAGE),
        zone='',zone_options=zone_options
    )

@app.route('/welcome/done', methods=['POST'])
@requires_open(redirect_to='index')
@requires_active_annotator(redirect_to='index')
def welcome_done():
    def tx():
        annotator = get_current_annotator()
        if request.form['action'] == 'Continue':
            annotator.read_welcome = True
        if 'next-zone' in request.form:
            annotator.zone = request.form['next-zone']

        db.session.commit()
    with_retries(tx)
    return redirect(url_for('index'))

def get_current_annotator():
    return Annotator.by_id(session.get(ANNOTATOR_ID, None))

def preferred_items(annotator):
    '''
    Return a list of preferred items for the given annotator to look at next.

    This method uses a variety of strategies to try to select good candidate
    projects.
    '''
    items = []
    ignored_ids = {i.id for i in annotator.ignore}

    '''
    Allow an item if it has not been ignored, and EITHER:
    - it is in the same zone and has not been viewed, OR
    - it is in a different zone from the annotator AND has been viewed
    '''

    if annotator.zone == "":
        available_items = Item.query.filter(and_(
            (Item.active == True),
            not_(Item.id.in_(ignored_ids)),
            not_(Item.viewed.any(Annotator.id == annotator.id))
        )).all()
    else:
        available_items = Item.query.filter(and_(
            (Item.active == True),
            not_(Item.id.in_(ignored_ids)),
            or_(
                and_(Item.zone != annotator.zone, Item.viewed.any(Annotator.id == annotator.id)),
                and_(Item.zone == annotator.zone, not_(Item.viewed.any(Annotator.id == annotator.id)))
        ))).all()

    prioritized_items = [i for i in available_items if i.prioritized]

    items = prioritized_items if prioritized_items else available_items

    annotators = Annotator.query.filter(
        (Annotator.active == True) & (Annotator.next != None) & (Annotator.updated != None)
    ).all()
    busy = {i.next.id for i in annotators if \
        (datetime.utcnow() - i.updated).total_seconds() < settings.TIMEOUT * 60}
    nonbusy = [i for i in items if i.id not in busy]
    preferred = nonbusy if nonbusy else items

    less_seen = [i for i in preferred if len(i.viewed) < settings.MIN_VIEWS]

    return less_seen if less_seen else preferred

def maybe_init_annotator():
    def tx():
        annotator = get_current_annotator()
        if annotator.next is None:
            items = preferred_items(annotator)
            if items:
                annotator.update_next(choice(items))
                db.session.commit()
    with_retries(tx)

def choose_next(annotator):
    items = preferred_items(annotator)

    shuffle(items) # useful for argmax case as well in the case of ties
    if items:
        if random() < crowd_bt.EPSILON:
            return items[0]
        else:
            return crowd_bt.argmax(lambda i: crowd_bt.expected_information_gain(
                annotator.alpha,
                annotator.beta,
                annotator.prev.mu,
                annotator.prev.sigma_sq,
                i.mu,
                i.sigma_sq), items)
    else:
        return None

def perform_vote(annotator, next_won):
    if next_won:
        winner = annotator.next
        loser = annotator.prev
    else:
        winner = annotator.prev
        loser = annotator.next
    u_alpha, u_beta, u_winner_mu, u_winner_sigma_sq, u_loser_mu, u_loser_sigma_sq = crowd_bt.update(
        annotator.alpha,
        annotator.beta,
        winner.mu,
        winner.sigma_sq,
        loser.mu,
        loser.sigma_sq
    )
    annotator.alpha = u_alpha
    annotator.beta = u_beta
    winner.mu = u_winner_mu
    winner.sigma_sq = u_winner_sigma_sq
    loser.mu = u_loser_mu
    loser.sigma_sq = u_loser_sigma_sq
