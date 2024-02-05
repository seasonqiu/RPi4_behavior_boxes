# python3: lever_task.py
"""
author: tian qiu
date: 2024-02-05
name: lever_task.py
goal: lever task for motor training
description:
    train the rat how to pull lever to get reward

"""
import importlib
from transitions import Machine
from transitions import State
from transitions.extensions.states import add_state_features, Timeout
import pysistence, collections
from icecream import ic
import logging
import time
from datetime import datetime
import os
from gpiozero import PWMLED, LED, Button
from colorama import Fore, Style
import logging.config
from time import sleep
import random
import threading
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.figure as fg
import numpy as np

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": True,
    }
)
# all modules above this line will have logging disabled

import sys
sys.path.insert(0,'/home/pi/RPi4_behavior_boxes/essential')
import behavbox


# adding timing capability to the state machine
@add_state_features(Timeout)
class TimedStateMachine(Machine):
    pass


class LeverTask(object):
    # pull lever get sugar
    # Define states. States where the animals is waited to make their decision

    def __init__(self, **kwargs):  # name and session_info should be provided as kwargs

        # if no name or session, make fake ones (for testing purposes)
        if kwargs.get("name", None) is None:
            self.name = "name"
            print(
                Fore.RED
                + Style.BRIGHT
                + "Warning: no name supplied; making fake one"
                + Style.RESET_ALL
            )
        else:
            self.name = kwargs.get("name", None)

        if kwargs.get("session_info", None) is None:
            print(
                Fore.RED
                + Style.BRIGHT
                + "Warning: no session_info supplied; making fake one"
                + Style.RESET_ALL
            )
            from fake_session_info import fake_session_info

            self.session_info = fake_session_info
        else:
            self.session_info = kwargs.get("session_info", None)
        ic(self.session_info)

        # initialize the state machine
        self.states = [
            State(name='inter_trial_interval',
                  on_enter=["enter_inter_trial_interval"],
                  on_exit=["exit_inter_trial_interval"]),
            Timeout(name='cue_state',
                    on_enter=["enter_cue_state"],
                    on_exit=["exit_cue_state"],
                    timeout=self.session_info["cue_timeout"],
                    on_timeout=["restart"]),
            Timeout(name='reward_available',
                    on_enter=["enter_reward_available"],
                    on_exit=["exit_reward_available"],
                    timeout=self.session_info["reward_delay"],
                    on_timeout=["restart"])
        ]
        self.transitions = [
            ['start_trial', 'inter_trial_interval', 'cue_state'],
            ['evaluate_reward', 'cue_state', 'reward_available'],
            ['restart', 'reward_available', 'inter_trial_interval']
        ]

        self.machine = TimedStateMachine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial='inter_trial_interval'
        )
        self.trial_running = False

        # trial statistics
        self.correct_trial_number = 0
        self.actual_trial_number = 0
        self.error_count = 0
        self.error_list = []
        self.early_error = False
        self.error_repeat = False

        self.event_name = ""
        # initialize behavior box
        self.box = behavbox.BehavBox(self.session_info)
        self.reward = self.box.reward
        self.reward_size = self.session_info["reward_size"]
        self.reward_check = False

        # for foragaing parameters
        # self.side_choice = None  # whether free choice is left or right
        # self.cue_state = None

        # for refining the lick detection
        self.pull_count = 0
        # self.LED_blink = False

        # session_statistics
        self.total_reward = 0

    ########################################################################
    # functions called when state transitions occur
    ########################################################################
    def run(self):
        if self.box.event_list:
            self.event_name = self.box.event_list.popleft()
        else:
            self.event_name = ""
        if self.state == "cue_state":
            if self.lever_pulled:
                self.pull_count += 1
                self.pull_count_list.append(self.pull_count)
                self.timeline_pulled.append(time.time())
                self.evaluate_reward()

        elif self.state == "reward_available":
            self.reward_check = True
            self.reward_count += 1
            self.restart()

        # look for keystrokes
        self.box.check_keybd()

    def enter_inter_trial_interval(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_inter_trial_interval;" + str(self.error_repeat))
        self.update_plot_choice()
        # self.update_plot_error()
        self.trial_running = False
        print(str(time.time()) + ", Total reward up till current session: " + str(self.total_reward))
        logging.info(";" + str(time.time()) + ";[trial];trial_" + str(self.actual_trial_number) + ";" + str(self.error_repeat))

    def exit_inter_trial_interval(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_inter_trial_interval;" + str(self.error_repeat))
        self.pull_count = 0
        self.box.event_list.clear()
        pass

    def enter_cue_state(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_cue_state;" + str(self.error_repeat))
        # turn on the cue according to the current card
        self.check_cue(self.current_cue) #(self.current_card[0])

    def exit_cue_state(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_cue_state;" + str(self.error_repeat))
        self.cue_off(self.current_cue) #(self.current_card[0])

    def enter_reward_available(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_reward_available;" + str(self.error_repeat))
        # print(str(time.time()) + ", " + str(self.actual_trial_number) + ", cue_state distance satisfied")

    def exit_reward_available(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_reward_available;" + str(self.error_repeat))
        if self.pull_count == 0:
            logging.info(";" + str(time.time()) + ";[error];no_choice_error;" + str(self.error_repeat))
            self.check_cue('sound2')
            # self.error_repeat = True
            self.error_count += 1
            self.error_list.append('no_choice_error')
        elif self.reward_check:
            logging.info(";" + str(time.time()) + ";[error];correct_trial;" + str(self.error_repeat))
            self.reward(self.reward_size)
            # self.error_repeat = False
            self.total_reward += 1
            self.reward_check = False
            self.error_list.append('correct_trial')

        self.wrong_choice_error = False


    def check_cue(self, cue):
        if cue == 'sound1':
            logging.info(";" + str(time.time()) + ";[cue];cue_sound1_on;" + str(self.error_repeat))
            self.box.sound1.on()
        if cue == 'sound2':
            logging.info(";" + str(time.time()) + ";[cue];cue_sound2_on;" + str(self.error_repeat))
            self.box.sound2.blink(1, 0.1, 1)
        elif cue == 'LED_L':
            self.box.cueLED1.on()
            logging.info(";" + str(time.time()) + ";[cue];cueLED_L_on;" + str(self.error_repeat))
        elif cue == 'LED_R':
            self.box.cueLED2.on()
            logging.info(";" + str(time.time()) + ";[cue];cueLED_R_on;" + str(self.error_repeat))
        elif cue == 'all':
            self.box.cueLED1.on()
            self.box.cueLED2.on()
            logging.info(";" + str(time.time()) + ";[cue];LED_L+R_on; " + str(self.error_repeat))

    def cue_off(self, cue):
        if cue == 'all':
            self.box.cueLED1.off()
            self.box.cueLED2.off()
        elif cue == 'sound1':
            self.box.sound1.off()
            logging.info(";" + str(time.time()) + ";[cue];cue_sound1_off;" + str(self.error_repeat))
        elif cue == 'sound2':
            self.box.sound2.off()
            logging.info(";" + str(time.time()) + ";[cue];cue_sound2_off;" + str(self.error_repeat))
        elif cue == 'LED_L':
            self.box.cueLED1.off()
            logging.info(";" + str(time.time()) + ";[cue];cueLED1_off;" + str(self.error_repeat))
        elif cue == 'LED_R':
            self.box.cueLED2.off()
            logging.info(";" + str(time.time()) + ";[cue];cueLED2_off;" + str(self.error_repeat))


    def update_plot(self):
        fig, axes = plt.subplots(1, 1, )
        axes.plot([1, 2], [1, 2], color='green', label='test')
        self.box.check_plot(fig)

    def update_plot_error(self):
        error_event = self.error_list
        labels, counts = np.unique(error_event, return_counts=True)
        ticks = range(len(counts))
        fig, ax = plt.subplots(1, 1, )
        ax.bar(ticks, counts, align='center', tick_label=labels)
        ax = plt.gca()
        ax.set_xticks(ticks, labels)
        ax.set_xticklabels(labels=labels, rotation=70)

        self.box.check_plot(fig)

    def update_plot_choice(self, save_fig=False):
        trajectory_left = self.left_poke_count_list
        time_left = self.timeline_left_poke
        trajectory_right = self.right_poke_count_list
        time_right = self.timeline_right_poke
        fig, ax = plt.subplots(1, 1, )
        print(type(fig))

        ax.plot(time_left, trajectory_left, color='b', marker="o", label='left_lick_trajectory')
        ax.plot(time_right, trajectory_right, color='r', marker="o", label='right_lick_trajectory')
        if save_fig:
            plt.savefig(self.session_info['basedir'] + "/" + self.session_info['basename'] + "/" + \
                        self.session_info['basename'] + "_choice_plot" + '.png')
        self.box.check_plot(fig)

    def integrate_plot(self, save_fig=False):

        fig, ax = plt.subplots(2, 1)

        trajectory_left = self.left_poke_count_list
        time_left = self.timeline_left_poke
        trajectory_right = self.right_poke_count_list
        time_right = self.timeline_right_poke
        print(type(fig))

        ax[0].plot(time_left, trajectory_left, color='b', marker="o", label='left_lick_trajectory')
        ax[0].plot(time_right, trajectory_right, color='r', marker="o", label='right_lick_trajectory')

        error_event = self.error_list
        labels, counts = np.unique(error_event, return_counts=True)
        ticks = range(len(counts))
        ax[1].bar(ticks, counts, align='center', tick_label=labels)
        # plt.xticks(ticks, labels)
        # plt.title(session_name)
        ax[1] = plt.gca()
        ax[1].set_xticks(ticks, labels)
        ax[1].set_xticklabels(labels=labels, rotation=70)

        if save_fig:
            plt.savefig(self.session_info['basedir'] + "/" + self.session_info['basename'] + "/" + \
                        self.session_info['basename'] + "_summery" + '.png')
        self.box.check_plot(fig)

    ########################################################################
    # methods to start and end the behavioral session
    ########################################################################

    def start_session(self):
        ic("TODO: start video")
        self.box.video_start()

    def end_session(self):
        ic("TODO: stop video")
        self.update_plot_choice(save_fig=True)
        self.box.video_stop()