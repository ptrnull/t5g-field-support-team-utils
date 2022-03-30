"""UI views for t5gweb"""
import logging
import datetime
from flask import (
    Blueprint, redirect, render_template, request, url_for, make_response, send_file, request
)
from t5gweb.t5gweb import (
    get_new_cases,
    get_new_comments,
    get_trending_cards,
    plots,
    set_cfg
)
from t5gweb.libtelco5g import(
    cache_cases,
    cache_cards,
    cache_bz,
    redis_get,
    generate_stats
)

BP = Blueprint('ui', __name__, url_prefix='/')

def load_data():
    """Load data for dashboard"""
    
    cfg = set_cfg()
    #new_cases = get_new_cases()
    load_data.new_cnv_cases = get_new_cases('cnv')
    load_data.new_t5g_cases = get_new_cases('shift_telco5g')
    plot_data = plots()
    load_data.y = list(plot_data.values())
    telco_accounts, cnv_accounts = get_new_comments()
    load_data.telco_comments = telco_accounts
    load_data.cnv_comments = cnv_accounts
    telco_accounts_all, cnv_accounts_all = get_new_comments(new_comments_only=False)
    load_data.telco_comments_all = telco_accounts_all
    load_data.cnv_comments_all = cnv_accounts_all
    load_data.trending_cards = get_trending_cards()
    load_data.now = redis_get('timestamp')

@BP.route('/')
def index():
    """list new cases"""
    load_data()
    return render_template('ui/index.html', new_cnv_cases=load_data.new_cnv_cases, new_t5g_cases=load_data.new_t5g_cases, values=load_data.y, now=load_data.now)

@BP.route('/refresh')
def refresh():
    """Forces an update to the dashboard"""
    cfg = set_cfg()
    cache_cards(cfg)
    load_data()
    return redirect(url_for("ui.telco5g"))

@BP.route('/updates/telco5g')
def telco5g():
    """Retrieves cards that have been updated within the last week and creates report"""
    load_data()
    return render_template('ui/updates.html', now=load_data.now, new_comments=load_data.telco_comments, page_title='telco5g')

@BP.route('/updates/telco5g/all')
def all_telco5g():
    """Retrieves all cards and creates report"""
    load_data()
    return render_template('ui/updates.html', now=load_data.now, new_comments=load_data.telco_comments_all, page_title='all-telco5g')

@BP.route('/updates/cnv')
def cnv():
    """Retrieves cards that have been updated within the last week and creates report"""
    load_data()
    return render_template('ui/updates.html', now=load_data.now, new_comments=load_data.cnv_comments, page_title='cnv')

@BP.route('/updates/cnv/all')
def all_cnv():
    """Retrieves all cards and creates report"""
    load_data()
    return render_template('ui/updates.html', now=load_data.now, new_comments=load_data.cnv_comments_all, page_title='all-cnv')

@BP.route('/trends')
def trends():
    """Retrieves cards that have been labeled with 'Trends' within the previous quarter and creates report"""
    load_data()
    return render_template('ui/updates.html', now=load_data.now, new_comments=load_data.trending_cards, page_title='trends')

@BP.route('/updates/telco5g/severity')
def telco_severity():
    """Sorts new telco5g cards by severity and creates table"""
    load_data()
    return render_template('ui/table.html', now=load_data.now, new_comments=load_data.telco_comments, page_title='telco5g-severity')

@BP.route('/updates/telco5g/all/severity')
def telco_all_severity():
    """Sorts all telco5g cards by severity and creates table"""
    load_data()
    return render_template('ui/table.html', now=load_data.now, new_comments=load_data.telco_comments_all, page_title='all-telco5g-severity')

@BP.route('/updates/cnv/severity')
def cnv_severity():
    """Sorts all telco5g cards by severity and creates table"""
    load_data()
    return render_template('ui/table.html', now=load_data.now, new_comments=load_data.cnv_comments, page_title='cnv-severity')

@BP.route('/updates/cnv/all/severity')
def cnv_all_severity():
    """Retrieves all cards and creates report"""
    load_data()
    return render_template('ui/table.html', now=load_data.now, new_comments=load_data.cnv_comments_all, page_title='all-cnv-severity')

@BP.route('/stats/<string:case_type>')
def get_stats(case_type):
    """ generate some stats for a given case type"""
    if case_type in ['telco5g', 'cnv']:
        stats = generate_stats(case_type)
        historical_stats = redis_get("{}_stats".format(case_type))
        logging.warning("all stats: {}".format(historical_stats))
        x_values = [day for day in historical_stats]
        y_values = {
            'escalated': [],
            'open_cases': [],
            'new_cases': [],
            'closed_cases': [],
            'no_updates': [],
            'no_bzs': [],
            'bugs_unique': [],
            'bugs_no_tgt': []
        }

        for day, stat in historical_stats.items():
            y_values['escalated'].append(stat['escalated'])
            y_values['open_cases'].append(stat['open_cases'])
            y_values['new_cases'].append(stat['daily_opened_cases'])
            y_values['closed_cases'].append(stat['daily_closed_cases'])
            y_values['no_updates'].append(stat['no_updates'])
            y_values['no_bzs'].append(stat['no_bzs'])
            y_values['bugs_unique'].append(stat['bugs']['unique'])
            y_values['bugs_no_tgt'].append(stat['bugs']['no_target'])
            
        logging.warning("days: {}".format(x_values))
        logging.warning("y: {}".format(y_values))
        now = str(datetime.datetime.utcnow())
        return render_template('ui/stats.html', now=now, stats=stats, x_values=x_values, y_values=y_values, page_title='stats/{}'.format(case_type))
    else:
        return {'error': 'unknown card type: {}'.format(case_type)}
