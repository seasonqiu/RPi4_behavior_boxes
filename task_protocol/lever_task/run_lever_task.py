#!/usr/bin/env -S ipython3 -i
# run_headfixed2FC_task.py
"""
author: tian qiu
date: 2024-02-05
name: run_lever_task.py
goal: movement study
description:
    first level training on animal using lever

"""
import random
import numpy as np
from transitions import Machine
from transitions import State
from icecream import ic
import logging
from datetime import datetime
import os
import logging.config
import pysistence, collections
import socket
import importlib
import colorama
import warnings
import scipy.io, pickle
import pygame
from colorama import Fore, Style
import time
from time import sleep

debug_enable = False

# all modules above this line will have logging disabled
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': True,
})

if debug_enable:
    # enabling debugger
    from IPython import get_ipython

    ipython = get_ipython()
    ipython.magic("pdb on")
    ipython.magic("xmode Verbose")

# import your task class here
from lever_task import LeverTask

try:
    # load in session_info file, check that dates are correct, put in automatic
    # time and date stamps for when the experiment was run

    datestr = datetime.now().strftime("%Y-%m-%d")
    timestr = datetime.now().strftime('%H%M%S')
    full_module_name = 'session_info_' + datestr

    import sys

    session_info_path = '/home/pi/experiment_info/lever_task/session_info'
    sys.path.insert(0, session_info_path)
    tempmod = importlib.import_module(full_module_name)
    session_info = tempmod.session_info
    mouse_info = tempmod.mouse_info

    session_info['date'] = datestr
    session_info['time'] = timestr
    session_info['datetime'] = session_info['date'] + '_' + session_info['time']
    session_info['basename'] = session_info['animal_name'] + '_' + session_info['datetime']
    session_info['dir_name'] = session_info['basedir'] + "/" + session_info['basename']

    if session_info['manual_date'] != session_info['date']:  # check if file is updated
        print('wrong date!!')
        raise RuntimeError('manual_date field in session_info file is not updated')

    # make data directory and initialize logfile
    os.makedirs(session_info['dir_name'])
    os.chdir(session_info['dir_name'])
    session_info['file_basename'] = session_info['dir_name'] + '/' + session_info['basename']

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d,[%(levelname)s],%(message)s",
        datefmt=('%H:%M:%S'),
        handlers=[
            logging.FileHandler(session_info['file_basename'] + '.log'),
            logging.StreamHandler()  # sends copy of log output to screen
        ]
    )

    # from task_information_lever import TaskInformation
    # task_information = TaskInformation()
    # print("Imported task_information_headfixed: " + str(task_information.name))
    task = LeverTask(name="LeverTask", session_info=session_info)

    if session_info['phase'] == "pull_lever_get_sugar":
        pass

    first_trial_of_the_session = True
    # # you can change various parameters if you want
    # task.machine.states['cue'].timeout = 2

    # start session
    task.start_session()
    scipy.io.savemat(session_info['file_basename'] + '_session_info.mat', {'session_info': session_info})
    pickle.dump(session_info, open(session_info['file_basename'] + '_session_info.pkl', "wb"))
    sleep(10)
    # loop over trials
    # Set a timer
    t_minute = int(input("Enter the time in minutes: ")) # wll add in the session info
    t_end = time.time() + 60 * t_minute
    while time.time() < t_end: # time check
        if not first_trial_of_the_session:
            print("reward_time_out: " + str(session_info["reward_timeout"]))
            sleep(session_info["reward_timeout"])
        else:
            first_trial_of_the_session = False
        # setup the beginning of a new trial
        task.error_count = 0 # reset the error count if previous trial is correct
        print("Trial " + str(task.actual_trial_number) + " \n")
        # task.correct_trial_number += 1
        # task.actual_trial_number += 1
        print("*******************************\n")
    logging.info(";" + str(time.time()) + ";current_reward_" + str(task.current_reward)[1:-1])
    logging.info(";" + str(time.time()) + ";[transition];start_trial()")
    task.start_trial()  # initiate the time state machine, start_trial() is a trigger
    while task.trial_running:
        task.run()  # run command trigger additional functions outside of the state machine
    print("error_count: " + str(task.error_count))
    raise SystemExit

# graceful exit
except (KeyboardInterrupt, SystemExit):
    print(Fore.RED + Style.BRIGHT + 'Exiting now...' + Style.RESET_ALL)
    ic('about to call end_session()')
    task.end_session()
    ic('just called end_session()')
    # save dicts to disk
    scipy.io.savemat(session_info['file_basename'] + '_session_info.mat', {'session_info': session_info})
    pickle.dump(session_info, open(session_info['file_basename'] + '_session_info.pkl', "wb"))
    pygame.quit()

# exit because of error
except RuntimeError as ex:
    print(Fore.RED + Style.BRIGHT + 'ERROR: Exiting now' + Style.RESET_ALL)
    # save dicts to disk
    scipy.io.savemat(session_info['file_basename'] + '_session_info.mat', {'session_info': session_info})
    pickle.dump(session_info, open(session_info['file_basename'] + '_session_info.pkl', "wb"))
    task.end_session()