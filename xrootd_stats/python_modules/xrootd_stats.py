import xml.etree.ElementTree as ET
import subprocess
import time
import socket

NAME_PREFIX = "xrd_"

info = {}
buff = {}
link = {}
poll = {}
sts = {}
proc = {}
xrootd = {}
ofs = {}
oss = {}
sched = {}
sgen = {}

Desc_Skel = {}
descriptors = []
test_descriptor = []
data = {'xml': '', 'time': ''}

root_metric_list = {
    NAME_PREFIX+'sys_src': {'type': 'string', 'format': '%s', 'description': 'Host/post reporting data'},
    NAME_PREFIX+'sys_ver': {'type': 'string', 'format': '%s', 'description': 'Version name'},
    NAME_PREFIX+'sys_tos': {'type': 'uint', 'format': '%u', 'description': 'Unix time when program was started'},
    NAME_PREFIX+'sys_pgm': {'type': 'string', 'format': '%s', 'description': 'Program name'},
    NAME_PREFIX+'sys_ins': {'type': 'string', 'format': '%s', 'description': 'Instance name'},
    NAME_PREFIX+'sys_pid': {'type': 'uint', 'format': '%u', 'description': 'Program\'s process ID'},
    NAME_PREFIX+'sys_site': {'type': 'string', 'format': '%s', 'description': 'Specified site name'},
}

info_metric_list = {
    NAME_PREFIX+'info_host': {'type': 'string', 'format': '%s', 'description': 'Hostname'},
    NAME_PREFIX+'info_port': {'type': 'uint', 'format': '%u', 'description': 'Port #'},
    NAME_PREFIX+'info_name': {'type': 'string', 'format': '%s', 'description': 'Instance name'},
}

link_metric_list = {
    NAME_PREFIX + 'link_num': {'type': 'uint', 'format': '%u', 'description': 'Current connections', 'units': 'link_num'},
    NAME_PREFIX + 'link_maxn': {'type': 'uint', 'format': '%u', 'description': 'Max # of simultaneous connections', 'units': 'link_maxn'},
    NAME_PREFIX + 'link_tot': {'type': 'uint', 'format': '%u', 'description': 'Connections since start-up', 'units': 'link_tot'},
    NAME_PREFIX + 'link_in': {'type': 'uint', 'format': '%u', 'description': 'Bytes received', 'units': 'bytes/sec'},
    NAME_PREFIX + 'link_out': {'type': 'uint', 'format': '%u', 'description': 'Bytes sent', 'units': 'bytes/sec'},
    NAME_PREFIX + 'link_ctime': {'type': 'uint', 'format': '%u', 'description': 'Cumulative # of connect seconds', 'units': 'link_ctime'},
    NAME_PREFIX + 'link_tmo': {'type': 'uint', 'format': '%u', 'description': 'Read request timeouts', 'units': 'link_tmo'},
    NAME_PREFIX + 'link_stall': {'type': 'uint', 'format': '%u', 'description': '# of times partial data was received', 'units': 'link_stall'},
    NAME_PREFIX + 'link_sfps': {'type': 'uint', 'format': '%u', 'description': 'Partial sendfile ops', 'units': 'link_sfps'},
}

poll_metric_list = {
    NAME_PREFIX + 'poll_att'	: {'type': 'uint', 'format': '%u', 'description': 'File descriptors attached for polling', 'units': 'poll_att'},
    NAME_PREFIX + 'poll_en'		: {'type': 'uint', 'format': '%u', 'description': 'Poll enable operations', 'units': 'poll_en'},
    NAME_PREFIX + 'poll_ev'		: {'type': 'uint', 'format': '%u', 'description': 'Polling events', 'units': 'poll_ev'},
    NAME_PREFIX + 'poll_int'	: {'type': 'uint', 'format': '%u', 'description': 'Unsolicited polling events', 'units': 'poll_int'},
}

buff_metric_list = {
    NAME_PREFIX+'buff_reqs': {'type': 'uint', 'format': '%u', 'description': 'Requests for a buffer', 'units': 'buff_reqs'},
    NAME_PREFIX+'buff_mem': {'type': 'uint', 'format': '%u', 'description': 'Bytes allocated to buffers', 'units': 'bytes'},
    NAME_PREFIX+'buff_buffs': {'type': 'uint', 'format': '%u', 'description': 'No of allocated buffer profile', 'units': 'buff_buffs'},
    NAME_PREFIX+'buff_adj': {'type': 'uint', 'format': '%u', 'description': 'Adjustments to the buffer profile', 'units': 'buff_adj'},
    NAME_PREFIX+'buff_xlreqs': {'type': 'uint', 'format': '%u', 'description': 'xlreqs', 'units': 'buff_xlreqs'},
    NAME_PREFIX+'buff_xlmem': {'type': 'uint', 'format': '%u', 'description': 'xlmem', 'units': 'buff_xlem'},
    NAME_PREFIX+'buff_xlbuffs': {'type': 'uint', 'format': '%u', 'description': 'xlbuffs', 'units': 'buff_xlbuffs'},
}

proc_metric_list = {
    NAME_PREFIX+'proc_usr_u': {'type': 'uint', 'format': '%u', 'description': 'Microseconds of user-time', 'units': 'sec'},
    NAME_PREFIX+'proc_usr_s': {'type': 'uint', 'format': '%u', 'description': 'Seconds of user-time', 'units': 'sec'},
    NAME_PREFIX+'proc_sys_s': {'type': 'uint', 'format': '%u', 'description': 'Seconds of system-time', 'units': 'sec'},
    NAME_PREFIX+'proc_sys_u': {'type': 'uint', 'format': '%u', 'description': 'Microseconds of user-time', 'units': 'sec'},
}

ofs_metric_list = {
    NAME_PREFIX + 'ofs_role': {'type': 'string', 	'format': '%s', 'description': 'Reporter\'s role', 'units': 'ofs_role'},
    NAME_PREFIX + 'ofs_opr'	: {'type': 'uint', 	'format': '%u', 'description': 'Files open in read-mode', 'units': 'ofs_opr'},
    NAME_PREFIX + 'ofs_opw'	: {'type': 'uint', 	'format': '%u', 'description': 'Files open in read/write mode', 'units': 'ofs_opw'},
    NAME_PREFIX + 'ofs_opp'	: {'type': 'uint', 	'format': '%u', 'description': 'Files open in read/write POSC mode', 'units': 'ofs_opp'},
    NAME_PREFIX + 'ofs_ups'	: {'type': 'uint', 	'format': '%u', 'description': 'Number of times a POSC mode file was un-persisted', 'units': 'ofs_ups'},
    NAME_PREFIX + 'ofs_han'	: {'type': 'uint', 	'format': '%u', 'description': 'Active file handlers', 'units': 'ofs_han'},
    NAME_PREFIX + 'ofs_rdr'	: {'type': 'uint', 	'format': '%u', 'description': 'Redirects processed', 'units': 'ofs_rdr'},
    NAME_PREFIX + 'ofs_bxq'	: {'type': 'uint', 	'format': '%u', 'description': 'Background tasks processed', 'units': 'ofs_bxq'},
    NAME_PREFIX + 'ofs_rep'	: {'type': 'uint',	    'format': '%u', 'description': 'Background replies processed', 'units': 'ofs_rep'},
    NAME_PREFIX + 'ofs_err'	: {'type': 'uint', 	'format': '%u', 'description': 'Errors encountered', 'units': 'ofs_err'},
    NAME_PREFIX + 'ofs_dly'	: {'type': 'uint', 	'format': '%u', 'description': 'Delays imposed', 'units': 'ofs_dly'},
    NAME_PREFIX + 'ofs_sok'	: {'type': 'uint', 	'format': '%u', 'description': 'Events received that indicated success', 'units': 'ofs_sok'},
    NAME_PREFIX + 'ofs_ser'	: {'type': 'uint', 	'format': '%u', 'description': 'Events received that indicated failure', 'units': 'ofs_ser'},
    NAME_PREFIX + 'ofs_grnt': {'type': 'uint', 	'format': '%u', 'description': '# of thid party copies allowed', 'units': 'ofs_grnt'},
    NAME_PREFIX + 'ofs_deny': {'type': 'uint', 	'format': '%u', 'description': '# of third party copies denied', 'units': 'ofs_deny'},
    NAME_PREFIX + 'ofs_err'	: {'type': 'uint', 	'format': '%u', 'description': '# of third party copies that failed', 'units': 'ofs_err'},
    NAME_PREFIX + 'ofs_exp'	: {'type': 'uint', 	'format': '%u', 'description': '# of third party copies whose auth expired', 'units': 'ofs_exp'},
}

oss_metric_list = {
    #NAME_PREFIX + 'oss_paths_lp': {'type': 'string', 'format': '%s', 'description': 'The minimally reduced logical file system path', 'units': 'oss_paths_lp'},
    #NAME_PREFIX + 'oss_paths_rp': {'type': 'string', 'format': '%s', 'description': 'The minimally reduced real file system path', 'units': 'oss_paths_rp'},
    NAME_PREFIX + 'oss_paths_tot': {'type': 'uint', 'format': '%u', 'description': 'Kilobytes allocated', 'units': 'bytes/sec'},
    NAME_PREFIX + 'oss_paths_free': {'type': 'uint', 'format': '%u', 'description': 'Kilobytes available', 'units': 'bytes/sec'},
    NAME_PREFIX + 'oss_paths_ino': {'type': 'uint', 'format': '%u', 'description': '# of inodes', 'units': 'oss_paths_ino'},
    NAME_PREFIX + 'oss_paths_ifr': {'type': 'uint', 'format': '%u', 'description': '# of free inodes', 'units': 'oss_paths_ifr'},
    NAME_PREFIX + 'oss_space_name': {'type': 'string', 'format': '%s', 'description': 'Name for the space', 'units': 'oss_space_name'},
    NAME_PREFIX + 'oss_space_tot': {'type': 'uint', 'format': '%u', 'description': 'Kilobytes allocated', 'units': 'bytes/sec'},
    NAME_PREFIX + 'oss_space_free': {'type': 'uint', 'format': '%u', 'description': 'Kilobytes available', 'units': 'bytes/sec'},
    NAME_PREFIX + 'oss_space_maxf': {'type': 'uint', 'format': '%u', 'description': 'Max kilobytes available in a filesystem extent', 'units': 'bytes'},
    NAME_PREFIX + 'oss_space_fsn': {'type': 'uint', 'format': '%u', 'description': '# of file system extents', 'units': 'oss_space_fsn'},
    NAME_PREFIX + 'oss_space_usg': {'type': 'uint', 'format': '%u', 'description': 'Usage associated with space name', 'units': 'oss_space_usg'},
}

xrootd_metric_list = {
    NAME_PREFIX+'xrootd_num': {'type': 'uint', 'format': '%u', 'description': '# of times the protocol was selected', 'units': 'xrootd_num'},
    NAME_PREFIX+'xrootd_ops_open': {'type': 'uint', 'format': '%u', 'description': 'File open reqs', 'units': 'xrootd_ops_open'},
    NAME_PREFIX+'xrootd_ops_rf': {'type': 'uint', 'format': '%u', 'description': 'Cache refresh reqs', 'units': 'xrootd_ops_rf'},
    NAME_PREFIX+'xrootd_ops_rd': {'type': 'uint', 'format': '%u', 'description': 'Read reqs', 'units': 'xrootd_ops_rd'},
    NAME_PREFIX+'xrootd_ops_pr': {'type': 'uint', 'format': '%u', 'description': 'Pre-read reqs', 'units': 'xrootd_ops_pr'},
    NAME_PREFIX+'xrootd_ops_rv': {'type': 'uint', 'format': '%u', 'description': 'Readv reqs', 'units': 'xrootd_ops_rv'},
    NAME_PREFIX+'xrootd_ops_rs': {'type': 'uint', 'format': '%u', 'description': 'Readv segments', 'units': 'xrootd_ops_rs'},
    NAME_PREFIX+'xrootd_ops_wr': {'type': 'uint', 'format': '%u', 'description': 'Write reqs', 'units': 'xrootd_ops_wr'},
    NAME_PREFIX+'xrootd_ops_sync': {'type': 'uint', 'format': '%u', 'description': 'Sync reqs', 'units': 'xrootd_ops_sync'},
    NAME_PREFIX+'xrootd_ops_getf': {'type': 'uint', 'format': '%u', 'description': 'Getfile reqs', 'units': 'xrootd_ops_getf'},
    NAME_PREFIX+'xrootd_ops_putf': {'type': 'uint', 'format': '%u', 'description': 'Putfile reqs', 'units': 'xrootd_ops_putf'},
    NAME_PREFIX+'xrootd_ops_misc': {'type': 'uint', 'format': '%u', 'description': '# of other reqs', 'units': 'xrootd_ops_misc'},
    NAME_PREFIX+'xrootd_aio_num': {'type': 'uint', 'format': '%u', 'description': 'Async I/O reqs processed', 'units': 'xrootd_aio_num'},
    NAME_PREFIX+'xrootd_aio_max': {'type': 'uint', 'format': '%u', 'description': 'Max simultaneous asyc I/O reqs', 'units': 'xrootd_aio_max'},
    NAME_PREFIX+'xrootd_aio_rej': {'type': 'uint', 'format': '%u', 'description': 'Async I/O reqs converted to sync I/O', 'units': 'xrootd_aio_rej'},
    NAME_PREFIX+'xrootd_err': {'type': 'uint', 'format': '%u', 'description': '# of reqs that ended with an error', 'units': 'xrootd_aio_err'},
    NAME_PREFIX+'xrootd_rdr': {'type': 'uint', 'format': '%u', 'description': '# of reqs that were redirected', 'units': 'xrootd_aio_rdr'},
    NAME_PREFIX+'xrootd_dly': {'type': 'uint', 'format': '%u', 'description': '# of reqs that ended with a delay', 'units': 'xrootd_aio_dly'},
    NAME_PREFIX+'xrootd_lgn_num': {'type': 'uint', 'format': '%u', 'description': '# of login attempts', 'units': 'xrootd_lgn_num'},
    NAME_PREFIX+'xrootd_lgn_af': {'type': 'uint', 'format': '%u', 'description': '# of authentication attempts', 'units': 'xrootd_lgn_af'},
    NAME_PREFIX+'xrootd_lgn_au': {'type': 'uint', 'format': '%u', 'description': '# of successful authenticated logins', 'units': 'xrootd_lgn_au'},
    NAME_PREFIX+'xrootd_lgn_ua': {'type': 'uint', 'format': '%u', 'description': '# of successful un-authentication logins', 'units': 'xrootd_lgn_ua'},
}

sgen_metric_list = {
    NAME_PREFIX + 'sgen_as': {'type': 'uint', 'format': '%u', 'description': 'Method of data gathering', 'units': 'sync/async'},
    NAME_PREFIX + 'sgen_et': {'type': 'uint', 'format': '%u', 'description': 'Elapsed milliseconds from start to completion of statistics', 'units': 'sec'},
    NAME_PREFIX + 'sgen_toe': {'type': 'uint', 'format': '%u', 'description': 'Unix time when statistics gathering ended', 'units': 'Unix time'},
}

sched_metric_list = {
    NAME_PREFIX + 'sched_jobs': {'type': 'uint', 'format': '%u', 'description': 'Jobs requiring a thread', 'units': 'sched_jobs'},
    NAME_PREFIX + 'sched_inq': {'type': 'uint', 'format': '%u', 'description': 'Number of jobs that are currently in run-queue', 'units': 'sched_inq'},
    NAME_PREFIX + 'sched_maxinq': {'type': 'uint', 'format': '%u', 'description': 'Longest run-queue length', 'units': 'sched_maxinq'},
    NAME_PREFIX + 'sched_threads': {'type': 'uint', 'format': '%u', 'description': '# of current scheduler threads', 'units': 'sched_threads'},
    NAME_PREFIX + 'sched_idle': {'type': 'uint', 'format': '%u', 'description': '# of scheduler threads waiting for work', 'units': 'sched_idle'},
    NAME_PREFIX + 'sched_tcr': {'type': 'uint', 'format': '%u', 'description': 'Thread creations', 'units': 'sched_tct'},
    NAME_PREFIX + 'sched_tde': {'type': 'uint', 'format': '%u', 'description': 'Thread destruction', 'units': 'sched_tde'},
    NAME_PREFIX + 'sched_tlimr': {'type': 'uint', 'format': '%u', 'description': '# of times the thread limit was reached', 'units': 'sched_tlmir'},
}


def get_xml_info():
    if len(data['xml']) == 0:
        get_fresh_data()

    if int(time.time()) - int(data['time']) > 30:
        get_fresh_data()


def get_fresh_data():
    cmd = 'xrdfs storage02.spacescience.ro query stats a'
    process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()

    data['xml'] = output
    data['time'] = int(time.time())


def get_root_attrib(name):
    root = ET.fromstring(data['xml'])
    for i in root.attrib:
        tag = NAME_PREFIX + "sys_" + i
        sts[tag] = root.get(i)

    return sts[name]


def get_info(name):
    root = ET.fromstring(data['xml'])
    for i in root.findall("stats"):
        if i.attrib['id'] == "info":
            for c in i.getchildren():
                tag = NAME_PREFIX + "info_" + c.tag
                info[tag] = c.text

    return info[name]


def get_link_metrics(name):
    root = ET.fromstring(data['xml'])
    for i in root.findall('stats'):
        if i.attrib['id'] == "link":
            for c in i.getchildren():
                tag = NAME_PREFIX + "link_" + c.tag
                link[tag] = c.text

    return link[name]


def get_poll_metrics(name):
    root = ET.fromstring(data['xml'])
    for i in root.findall("stats"):
        if i.attrib['id'] == "poll":
            for c in i.getchildren():
                tag = NAME_PREFIX + "poll_" + c.tag
                poll[tag] = c.text

    return poll[name]


def get_buff_metrics(name):
    root = ET.fromstring(data['xml'])
    for i in root.findall('stats'):
        if i.attrib['id'] == "buff":
            for c in i.getchildren():
                tag = NAME_PREFIX + "buff_" + c.tag
                buff[tag] = c.text
    return buff[name]


def get_proc_metrics(name):
    root = ET.fromstring(data['xml'])
    for i in root.findall("stats"):
        if i.attrib['id'] == "proc":
            for c in i.getchildren():
                if c.tag == "usr":
                    for num in xrange(len(c.getchildren())):
                        tag = NAME_PREFIX + "proc_usr_" + c.getchildren()[num].tag
                        proc[tag] = c.getchildren()[num].text
                if c.tag == "sys":
                    for num in xrange(len(c.getchildren())):
                        tag = NAME_PREFIX + "proc_sys_" + c.getchildren()[num].tag
                        proc[tag] = c.getchildren()[num].text

    return proc[name]


def get_xrootd_metrics(name):
    root = ET.fromstring(data['xml'])
    for i in root.findall("stats"):
        if i.attrib['id'] == "xrootd":
            for c in i.getchildren():
                if c.tag not in ["ops", "aio", "lgn"]:
                    tag = NAME_PREFIX + "xrootd_" + c.tag
                    xrootd[tag] = c.text
                if c.tag == "ops":
                    for num in xrange(len(c.getchildren())):
                        tag = NAME_PREFIX+"xrootd_ops_"+c.getchildren()[num].tag
                        xrootd[tag] = c.getchildren()[num].text
                if c.tag == "aio":
                    for num in xrange(len(c.getchildren())):
                        tag = NAME_PREFIX+"xrootd_aio_"+c.getchildren()[num].tag
                        xrootd[tag] = c.getchildren()[num].text
                if c.tag == "lgn":
                    for num in xrange(len(c.getchildren())):
                        tag = NAME_PREFIX+"xrootd_lgn_"+c.getchildren()[num].tag
                        xrootd[tag] = c.getchildren()[num].text

    return xrootd[name]


def get_ofs_metrics(name):
    root = ET.fromstring(data['xml'])
    for i in root.findall("stats"):
        if i.attrib['id'] == "ofs":
            for c in i.getchildren():
                if c.tag not in ["tpc"]:
                    tag = NAME_PREFIX + "ofs_" + c.tag
                    ofs[tag] = c.text
                if c.tag == "tpc":
                    for num in xrange(len(c.getchildren())):
                        tag = NAME_PREFIX + "ofs_" + c.getchildren()[num].tag
                        ofs[tag] = c.getchildren()[num].text

    return ofs[name]


def get_oss_metrics(name):
    root = ET.fromstring(data['xml'])
    for i in root.findall("stats"):
        if i.attrib['id'] == "oss":
            s = i.find("paths").getchildren()
            ss = i.find("space").getchildren()

            for x in xrange(len(s)):
                for f in s[x].getchildren():
                    tag = NAME_PREFIX + "oss_paths_" + f.tag
                    oss[tag] = f.text

            for x in xrange(len(ss)):
                for f in ss[x].getchildren():
                    tag = NAME_PREFIX + "oss_space_" + f.tag
                    oss[tag] = f.text

    return oss[name]


def get_sgen_metrics(name):
    root = ET.fromstring(data['xml'])
    for i in root.findall("stats"):
        if i.attrib['id'] == "sgen":
            for c in i.getchildren():
                tag = NAME_PREFIX + "sgen_" + c.tag
                sgen[tag] = c.text

    return sgen[name]


def get_sched_metrics(name):
    root = ET.fromstring(data['xml'])
    for i in root.findall("stats"):
        if i.attrib['id'] == "sched":
            for c in i.getchildren():
                tag = NAME_PREFIX + "sched_" + c.tag
                sched[tag] = c.text

    return sched[name]


def metric_init(params):
    global descriptors, Desc_Skel

    if 'port' in params:
        _port = params['port']

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', int(_port)))
    if result == 0:
        get_xml_info()
    else:
        s = '<statistics tod="0" ver="0" src="0" tos="0" pgm="0" ins="0" pid="0" site="ALICE::ISS::FILE"><stats id="info"><host>0</host><port>0</port><name>0</name></stats><stats id="buff"><reqs>0</reqs><mem>0</mem><buffs>0</buffs><adj>0</adj><xlreqs>0</xlreqs><xlmem>0</xlmem><xlbuffs>0</xlbuffs></stats><stats id="link"><num>0</num><maxn>0</maxn><tot>0</tot><in>0</in><out>0</out><ctime>0</ctime><tmo>0</tmo><stall>0</stall><sfps>0</sfps></stats><stats id="poll"><att>0</att><en>0</en><ev>0</ev><int>0</int></stats><stats id="proc"><usr><s>0</s><u>0</u></usr><sys><s>0</s><u>0</u></sys></stats><stats id="xrootd"><num>0</num><ops><open>0</open><rf>0</rf><rd>0</rd><pr>0</pr><rv>0</rv><rs>0</rs><wr>0</wr><sync>0</sync><getf>0</getf><putf>0</putf><misc>0</misc></ops><aio><num>0</num><max>0</max><rej>0</rej></aio><err>0</err><rdr>0</rdr><dly>0</dly><lgn><num>0</num><af>0</af><au>0</au><ua>0</ua></lgn></stats><stats id="ofs"><role>server</role><opr>0</opr><opw>0</opw><opp>0</opp><ups>0</ups><han>0</han><rdr>0</rdr><bxq>0</bxq><rep>0</rep><err>0</err><dly>0</dly><sok>0</sok><ser>0</ser><tpc><grnt>0</grnt><deny>0</deny><err>0</err><exp>0</exp></tpc></stats><stats id="oss" v="2"><paths>1<stats id="0"><lp>0</lp><rp>0</rp><tot>0</tot><free>0</free><ino>0</ino><ifr>0</ifr></stats></paths><space>1<stats id="0"><name>0</name><tot>0</tot><free>0</free><maxf>0</maxf><fsn>0</fsn><usg>0</usg></stats></space></stats><stats id="sched"><jobs>0</jobs><inq>0</inq><maxinq>0</maxinq><threads>0</threads><idle>0</idle><tcr>0</tcr><tde>0</tde><tlimr>0</tlimr></stats><stats id="sgen"><as>0</as><et>0</et><toe>0</toe></stats></statistics>'
        data['xml'] = s

    Desc_Skel = {
        'name': 'XXX',
        'call_back': get_info,
        'time_max': 60,
        'value_type': 'uint',
        'format': '%d',
        'units': '#',
        'description': 'XXX',
        'groups': 'xrootd_stats',
    }

    for k, v in root_metric_list.iteritems():
        descriptors.append(create_desc(Desc_Skel, {
            'name': k,
            'call_back': get_root_attrib,
            'value_type': v['type'],
            'format': v['format'],
            'description': v['description']
        }))

    for k, v in info_metric_list.iteritems():
        descriptors.append(create_desc(Desc_Skel , {
            'name': k,
            'call_back': get_info,
            'value_type': v['type'],
            'format': v['format'],
            'description': v['description']
        }))

    for k, v in link_metric_list.iteritems():
        descriptors.append(create_desc(Desc_Skel, {
            'name': k,
            'call_back': get_link_metrics,
            'value_type': v['type'],
            'format': v['format'],
            'units': v['units'],
            'description': v['description']
        }))

    for k, v in poll_metric_list.iteritems():
        descriptors.append(create_desc(Desc_Skel, {
            'name': k,
            'call_back': get_poll_metrics,
            'value_type': v['type'],
            'units': v['units'],
            'format': v['format'],
            'description': v['description']
        }))

    for k, v in buff_metric_list.iteritems():
        descriptors.append(create_desc(Desc_Skel, {
            'name': k,
            'call_back': get_buff_metrics,
            'value_type': v['type'],
            'format': v['format'],
            'units': v['units'],
            'description': v['description']
        }))

    for k, v in proc_metric_list.iteritems():
        descriptors.append(create_desc(Desc_Skel , {
            'name': k,
            'call_back': get_proc_metrics,
            'value_type': v['type'],
            'format': v['format'],
            'units': v['units'],
            'description': v['description']
        }))

    for k, v in xrootd_metric_list.iteritems():
        descriptors.append(create_desc(Desc_Skel, {
            'name': k,
            'call_back': get_xrootd_metrics,
            'value_type': v['type'],
            'units': v['units'],
            'format': v['format'],
            'description': v['description']
        }))

    for k, v in oss_metric_list.iteritems():
        descriptors.append(create_desc(Desc_Skel, {
            'name': k,
            'call_back': get_oss_metrics,
            'value_type': v['type'],
            'format': v['format'],
            'units': v['units'],
            'description': v['description']
        }))

    for k, v in ofs_metric_list.iteritems():
        descriptors.append(create_desc(Desc_Skel, {
            'name': k,
            'call_back': get_ofs_metrics,
            'value_type': v['type'],
            'format': v['format'],
            'units': v['units'],
            'description': v['description']
        }))

    for k, v in sched_metric_list.iteritems():
        descriptors.append(create_desc(Desc_Skel, {
            'name': k,
            'call_back': get_sched_metrics,
            'value_type': v['type'],
            'format': v['format'],
            'units': v['units'],
            'description': v['description']
        }))

    for k, v in sgen_metric_list.iteritems():
        descriptors.append(create_desc(Desc_Skel, {
            'name': k,
            'call_back': get_sgen_metrics,
            'value_type': v['type'],
            'units': v['units'],
            'format': v['format'],
            'description': v['description']
        }))

    sock.close()

    return descriptors


def create_desc(skel, prop):
    d = skel.copy()
    for k, v in prop.iteritems():
        d[k] = v

    return d


def metric_cleanup():
    pass


if __name__ == "__main__":
    params = {'port': '1094'}
    metric_init(params)

    for d in descriptors:
        v = d['call_back'](d['name'])
        print d['name'], v
