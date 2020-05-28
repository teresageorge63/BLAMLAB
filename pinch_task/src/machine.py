from transitions import Machine

class HandSetupMachine(Machine):
    def __init__(self):
        states = ['pre_trial',
                  'moving']

        pre_trial_t = {'source': 'pre_trial',
                       'trigger': 'step',
                       'conditions': 'wait_for_space',
                       'after': ['reset_baseline',
                                 'start_trial_countdown'],
                       'dest': 'moving'}

        moving_t = {'source': 'moving',
                    'prepare': [],
                    'trigger': 'step',
                    'conditions': 'time_elapsed',
                    'after': ['start_trial_countdown'],
                    'dest': 'pre_trial'}

        transitions = [pre_trial_t, moving_t]
        Machine.__init__(self, states=states,
                         transitions=transitions, initial='pre_trial')


class GripStateMachine(Machine):
    def __init__(self):
        states = ['pre_trial',  # wait for the space press to start, and show text instruction on the screen
                  # after space press, start countdown timer and show target (5 sec to be within n dist of target)
                  'moving',
                  'hold_in_target',  # restart countdown timer for 1s
                  'post_trial',
                  'post_exp']  # if more than half of time was in target, happy. Remove target and wait ~1s

        
        pre_trial_t = {'source': 'pre_trial',
                       'trigger': 'step',
                       'conditions': ['time_elapsed','wait_for_space'],
                       'after': ['delete_file',
                                 'reset_baseline',
                                 'start_trial_countdown',
                                 'show_target'],
                       'dest': 'moving'}
        # prepare
        moving_t = {'source': 'moving',
                    'prepare': ['log_text'],
                    'trigger': 'step',
                    'conditions': 'close_to_target',
                    'after': 'start_hold_countdown',  # wait 0.5s
                    'dest': 'hold_in_target'}

        moving_t2 = {'source': 'moving',
                     'prepare': [],
                     'trigger': 'step',
                     'conditions': 'time_elapsed',  # check if countdown timer is negative
                     'after': ['hide_target', 'stoplog_text',
                              'start_post_countdown',
                              ],
                     'dest': 'post_trial'}

        # hold in target
        hold_in_target_t = {'source': 'hold_in_target',
                            'prepare': [],
                            'trigger': 'step',
                            'conditions': 'check_hold',
                            'after': ['play_success','hide_target','stoplog_text',
                                      'start_post_countdown'],
                            'dest': 'post_trial'}

        hold_in_target_t2 = {'source': 'hold_in_target',
                            'prepare': [],
                            'trigger': 'step',
                            'conditions': 'time_elapsed',
                            'after': ['hide_target','stoplog_text','start_post_countdown'],
                            'dest': 'post_trial'}

        post_trial_t = {'source': 'post_trial',
                        'trigger': 'step',
                        'conditions': ['time_elapsed',
                                       'trial_counter_exceeded'],
                        'after': 'start_post_countdown', # run sys.exit
                        'dest': 'post_exp'}

        post_trial_t2 = {'source': 'post_trial',
                         'trigger': 'step',
                         'conditions': 'time_elapsed',
                         'after': ['increment_trial_counter',
                                   'start_post_countdown',
                                   'reset_keyboard_bool'],
                         'dest': 'pre_trial'}

        post_exp_t = {'source': 'post_exp',
                      'trigger': 'step',
                      'conditions': 'time_elapsed',
                      'after': 'clean_up',
                      'dest': 'post_exp'}
        

        transitions = [pre_trial_t, moving_t, moving_t2,
                       hold_in_target_t, hold_in_target_t2, post_trial_t, post_trial_t2,pre_trial_t, post_exp_t]

        Machine.__init__(self, states=states,
                         transitions=transitions, initial='pre_trial')

        self.sv = 1 
        self.conditions={  # each state 
            'pre_trial': 1,
            'moving': 2,
            'hold_in_target': 3,
            'post_trial': 4,
            'post_exp':5,
        }

    def poll(self):
        if self.sv >= self.conditions[self.state]:
            self.next_state()

    def checkstate(self):
        return self.conditions[self.state]
