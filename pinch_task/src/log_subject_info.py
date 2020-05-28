from psychopy import gui
import yaml
import os
import datetime

class LogSubjectInfo:
    DATA_DIR = 'data'
    Gender = ['Male', 'Female', 'Other']
    Subject_type = ['Younger Control', 'Elderly control', 'Expert', 'Stroke patient']
    Hand = ['Left', 'Right']
    Finger = ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky']

    now = datetime.datetime.now()
    subj_dict = {'Subject ID': 'Ind001',
                 'Date (fmt:yyyy-mm-dd)': str(now)[:10],
                 'Gender': Gender,
                 'Subject_type': Subject_type,
                 'Session ID': 'A1',
                 'Assessment': False,
                 'Training': False,
                 'Session No.': 1,
                 'Hand': Hand,
                 'Handedness': 'R',
                 'Paretic side': '',
                 'Patient Note(Optional)': ''}
    subj_key_order = ['Subject ID','Date (fmt:yyyy-mm-dd)','Gender','Subject_type',
                       'Session ID','Assessment','Training','Session No.',
                       'Hand','Handedness','Patient Note(Optional)']
    hand_geom_dict = list({} for i in range(5))
    for i in range(5):
        hand_geom_dict[i] = {'MCP angle': '',
                             'PIP angle': '',
                             'DIP angle': '',
                             'Segment 1 Length': '',
                             'Segment 2 Length': '',
                             'Segment 3 Length':'',
                             'Finger cup size':'',
                             'DEVICE Mount length': '',
                             'DEVICE Mount angle': ''}
    hand_key_order = ['MCP angle','PIP angle','DIP angle',
                      'Segment 1 Length','Segment 2 Length','Segment 3 Length',
                      'Finger cup size','DEVICE Mount length','DEVICE Mount angle']
    all_data = {'Subject': subj_dict,
                'Thumb': hand_geom_dict[0],
                'Index': hand_geom_dict[1],
                'Middle': hand_geom_dict[2],
                'Ring': hand_geom_dict[3],
                'Pinky': hand_geom_dict[4]}

    def __init__(self,id,session,hand,wrist,exp):
        self.sub_id = id
        self.hand = hand
        self.session = session
        self.wrist = wrist
        self.exp = exp

        self.session_dir = os.path.join(self.DATA_DIR,'exp_' + self.exp,self.sub_id,self.session,self.wrist,self.hand)
        self.exp1_dir = os.path.join(self.DATA_DIR,'exp_1',self.sub_id,self.session,self.wrist,self.hand)
        self.exp2_dir = os.path.join(self.DATA_DIR,'exp_2',self.sub_id,self.session,self.wrist,self.hand)
        log_file_name =  self.sub_id + '_' + self.session + '_' + self.hand +'_log.yml'
        log_data = {}
        try:
            with open(os.path.join(self.session_dir,log_file_name)) as f:
                log_data = yaml.load(f)
        except:
            try:
                with open(os.path.join(self.exp2_dir,log_file_name)) as f:
                    log_data = yaml.load(f)
            except:
                try:
                    with open(os.path.join(self.exp1_dir,log_file_name)) as f:
                        log_data = yaml.load(f)
                except:
                    print("Found no log file for " + self.sub_id + "_" + self.session + '_' + self.hand + ". Making a new one.")

        # assign dictionary keys from loaded file
        if log_data:
            self.subj_dict = log_data['Subject']
        self.subj_dict['Subject ID'] = self.sub_id
        self.subj_dict['Session ID'] = self.session
        self.subj_dict['Hand'] = self.hand
        self.subj_dict['Date (fmt:yyyy-mm-dd)'] = str(datetime.datetime.now())[:10]
        self.all_data['Subject'] = self.subj_dict
        dialog = gui.DlgFromDict(dictionary=self.subj_dict, title='Subject Info', order=self.subj_key_order)
        for x in self.Finger:
            if log_data:
                self.hand_geom_dict[self.Finger.index(x)] = log_data[str(x)]
            dialog = gui.DlgFromDict(dictionary=self.hand_geom_dict[self.Finger.index(x)], title=str(x), order=self.hand_key_order)
            self.all_data[str(x)] = self.hand_geom_dict[self.Finger.index(x)]
        # saving data
        if dialog.OK:
            if not os.path.exists(self.session_dir):
                print("Making new folders: " + self.session_dir)
                os.makedirs(self.session_dir)
            with open(os.path.join(self.session_dir,log_file_name), "w") as f:
                 yaml.dump(self.all_data,f, default_flow_style=False)
        if not dialog.OK:
             os.sys.exit()
