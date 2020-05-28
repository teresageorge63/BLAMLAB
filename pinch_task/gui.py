import subprocess
from psychopy import gui#, visual, monitors
import sys

#win = visual.Window(size=[1920,1080],allowGUI=False)

subj_info = gui.Dlg(title="Pinch Task")
subj_info.addText('Subject info')
subj_info.addField('Subject ID:','Pin001')
subj_info.addField('Session ID:','A1')
subj_info.addField('Hand:',choices=["Right", "Left"])
subj_info.addField('Wrist:',choices=["flex","pron"])
subj_info.addText('Experiment Info')
subj_info.addField('Experiment:',choices=['1','2','3'])
subj_data = subj_info.show()  # show dialog and wait for OK or Cancel

setup = gui.Dlg(title="Pinch Task")
setup.addText('Setup')
setup.addField('Trial No:', 1)

exp = gui.Dlg(title="Pinch Task")
exp.addText('Experiment')
exp.addField('Block:', 0)
exp.addField('Task:', True)

while True:
    if subj_info.OK:  # or if ok_data is not None
        subprocess.call(["python","subj_info.py","--id",subj_data[0],"--session",subj_data[1],
            "--hand",subj_data[2],"--wrist",subj_data[3],"--exp",subj_data[4]])
        setup_data = setup.show()
    else:
        print('user cancelled')
        break

    if setup.OK:
        subprocess.call(["python","setup.py","--id",subj_data[0],"--session",subj_data[1],
            "--hand",subj_data[2],"--wrist",subj_data[3],"--exp",subj_data[4],
            "--trial",str(setup_data[0])])
        input('Setup...')
        subprocess.call(["python","subj_info.py","--id",subj_data[0],"--session",subj_data[1],
            "--hand",subj_data[2],"--wrist",subj_data[3],"--exp",subj_data[4]])
        exp_data = exp.show()
    else:
        print('setup cancelled')
        exp_data = exp.show()

    while True:
        if exp.OK:
            print(subj_data)
            print(exp_data)
            if exp_data[1] == True:
                task = 'task'
            else:
                task = 'demo'
            subprocess.call(["python","exp.py","--id",subj_data[0],"--session",subj_data[1],
                "--hand",subj_data[2],"--wrist",subj_data[3],"--exp",subj_data[4],
                "--blk",str(exp_data[0]),"--mode",task])
            exp_data = exp.show()
        else:
            print('experiment %s complete' % subj_data[4])
            subj_info.show()
            break
sys.exit()