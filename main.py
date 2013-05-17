###############################################################################
#                                                                             #
#  main.py                                                                    #
# main file for the Vox bot. Contains Bot() (And temporarily a few modules)   #
# main.py is a part of the Vox Bot project by JT "DarkFlame" Johnson          #
#                                                                             #
#                                                                             #
# This file is part of Vox Bot.                                               #
#                                                                             #
# Vox Bot is free software: you can redistribute it and/or modify             #
# it under the terms of the GNU General Public License as published by        #
# the Free Software Foundation, either version 3 of the License, or           #
# (at your option) any later version.                                         #
#                                                                             #
# Vox Bot is distributed in the hope that it will be useful,                  #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU General Public License for more details.                                #
#                                                                             #
# You should have received a copy of the GNU General Public License           #
# along with Vox Bot.  If not, see <http://www.gnu.org/licenses/>.            #
#                                                                             #
###############################################################################

import sys
import os
import time
import datetime
import threading

#import mechanize


    # Add dynamic module loading
#TODOs:

    # Refactor modules to be consistent
    # Make the bot save to one big state file which contains info for every mod
    #and the main bot itself. Pick which mods to load based on the contents of
    #this file.
    # Move modules into their own files and allow dynamic module loading.


    # Make more modules:

        # Steamgifts bot
        # DeviantArt message notifier
        # Googler

# For Python 2.x compatibility
try:
    input = raw_input
except NameError:
    pass


class Module(threading.Thread):

    """Base Module class
    All modules should inherit this class.
    This class should not be directly instantiated.

    Defines:
        __init__ (name, parent)
        run ()
            The mainloop of this module. It's started when the thread is begun
            with start()
        out (message)
            The interface for the thread to output in a uniform way.
    Hook functions:
        save_state ()
            Save the module's state to a file. Should be overridden by the
                subclass.
        load_state ()
            Load the state from the same file as save_state() uses.
        gear ()
            Mainloop operations function for each thread to add custom
                operations"""

    def __init__(self, name, parent):
        "Module initialization function. Make sure this runs for each subclass"
        super(Module, self).__init__(name=name)
        self.name = name

        self.parent = parent
        # updatetime should be overridden by subclasses. It is the time in sec-
        #onds between updates for the module.
        self.updatetime = 0.

        self.cmds = {}

        # This is used for checking to see if the thread needs to be quit.
        self.event = threading.Event()

    def run(self):
        """This function is run when the main thread calls the start() function
        from threading.Thread.
        It loads the state (If possible), then starts the mainloop."""
        # Start off by attempting to load the state from the last session. If
        #it can't do so, load_state() will just leave everything at defaults.
        self.load_state()
        while not self.parent.done:
            try:
                # The main execution function for the module's mainloop.
                self.gear()
            except Exception as e:
                #TODO Find out if this works
                # The theory here is that an error in the gear function will be
                #caught by this except block and exit gracefully.
                sys.stderr.write("ERROR in thread %s. Error message: '%s'" %
                    (self.name, e))
                #TODO Make it actually back up like it says it does
                sys.stderr.write("backing up state and exiting.")
                self.parent.done = True
                return

            # time.sleep(self.updatetime)
            interrupted = self.event.wait(self.updatetime)
            # If the thread was interrupted, not timed out
            if interrupted:
                #TODO Make it back up the state file in case of corruption
                self.out("Thread closing at %s" % time.asctime())
                self.save_state()
                return
        # Execution is complete, save the state to a file for the next session.
        self.save_state()

    def out(self, message):
        """Default output method for modules.
        Format:
            [HR:MN:SC] [ModuleName] Message
        """
        sys.stdout.write(time.strftime("[%H:%M:%S] "))
        sys.stdout.write("[%s] " % self.name)
        sys.stdout.write(str(message))
        sys.stdout.write('\n')

    def save_state(self):
        "Hook function for saving module state."
        pass

    def load_state(self):
        "Hook function for loading module state."
        pass

    def gear(self):
        "Hook function for mainloop logic."
        pass


#TODO Move custom modules to external .py files
class RemindersModule(Module):
    """reminders module
    This module lets the user set a time for an alarm to go off. When that time
    arrives, it shouts at the user, notifying them the alarm has ended.

    New definitions:
        add_alarm(name, time)iter
            adds alarm with name 'name' at time 'time'

        Command definitions:
            addreminder()
                Lets the user add a reminder with interactive input.
            listerminders():
                Uses out() to output all the reminders in a nice format."""

    def __init__(self, name, parent):
        "RemindersModule __init__ function."
        super(RemindersModule, self).__init__(name=name, parent=parent)

        # A dictionary of all the user-added modules. Right now, the format is
        #to have "name":"hr:mn"
        #TODO Rework how reminders are stored. Use datetimes
        self.reminders = {}
        self.updatetime = 5.

        self.cmds['reminders add'] = self.addreminder
        self.cmds['reminders list'] = self.listreminders
        #TODO Consider making it save as "%s" % self.name.upper()
        self.statefilename = "REMINDERS"

    def gear(self):
        "RemindersModule gear function."
        #TODO Rework how alarms are checked using datetimes rather than strings
        for al in list(self.reminders.keys()):
            tmstring = self.reminders[al]
            hr = int(tmstring[:tmstring.index(":")])
            mn = int(tmstring[tmstring.index(":") + 1:])

            t = time.localtime(time.time())
            if t.tm_hour == hr:
                if t.tm_min == mn:
                    self.out("====%s!====" % al)
                    del self.alarms[al]

    def save_state(self):
        "Saves reminders in a file."
        f = file(self.statefilename, 'w')

        for reminder in list(self.alarms.keys()):
            #TODO Error here with time format (Datetimes should fix)
            tstring = time.strftime("%B %d, %Y. %H:%M:00",
                self.alarms[reminder])
            #TODO redo the way alarms are saved to the file. Perhaps XML?
            #TODO Maybe make all states save into one central file
            f.write("%s|%s\n" % (reminder, tstring))
        f.close()

    def load_state(self):
        "Loads reminders from a file, if it exists."
        if not os.path.exists(self.statefilename):
            self.out("State file doesn't exist, clean slate.")
            # There isn't a valid states file, just continue like this. All
            #lists and dicts will just be empty.
            return
        #TODO New way to store states.
        f = file(self.statefilename, 'r')
        for line in f.readlines():
            n = line[:line.index("|")]
            d = line[line.index("|") + 1:-1]
            self.reminders[n] = time.strptime(d, "%B %d, %Y. %H:%M:00")

    ## Module-Specific Commands ##
    def addreminder(self):
        """Adds a reminder to the existing ones.
        Asks for a name and then the time.
                #TODO Make it actually back up like it says it does
        If the user inputs a bad time format, it cancels and the user has to
        start over."""
        self.out("Adding reminder...")
        name = input("Name? ")
        #TODO Better way to input the time
        #TODO Options for a specific day to make the alarm
        #TODO Option for a repeating alarm (Do not remove from list when done)

        datestr = input("Date? (mm/dd/yy) ")
        try:
            date = datetime.date.fromtimestamp(datestr, "%d/%b/%y")
        except ValueError as e:
            self.out("Bad time format '%s'" % e)

        timestr = input("Time? (hh:mm am/pm) ")
        "%I:%M %p"


        #t = input("Time? ('hr:mn')\n")
        #if not ":" in t:
            #self.out("Bad time format ('hr:mn')")
            #return
        #try:
            #int(t[:t.index(":")])
            #int(t[t.index(":") + 1:])
        #except ValueError:
            #self.out("Bad time format ('hr:mn')")
            #return

        #self.alarms[n] = t
        #self.out("Alarm '%s' added at %s." % (n, t))
        self.save_state()

    def listreminders(self):
        'Prints out each reminder in the format "Name - Time"'
        #TODO Somewhat redundant, Vox has this capability.
        self.out("Listing alarms...")
        for al in list(self.reminders.keys()):
            sys.stdout.write("    %s - %s\n" % (al, self.reminders[al]))


class TasksModule(Module):
    """Todo Module
    This module tracks todo items in a list, with an optional due date.
    When a todo item is completed, it is removed from the list altogether.
    On the day that it is due, it will begin to pester the user about it
    every 30 minutes.

    New Definitions:
        Command Definitions:
            addtodo()
                Lets the user add a todo item interactively.
            removetodo()
                Marks the item as finished and thus deletes it."""

    def __init__(self, name, parent):
        "TasksModule __init__ function"
        super(TasksModule, self).__init__(name=name, parent=parent)
        # self.updatetime = 60*60 # 60 seconds times 60 minutes = 1 hour.
        self.updatetime = 30 * 60  # 60 seconds times 30 minutes = 1 hour.
        #TODO Rename to 'Tasks'?

        self.cmds['todo add'] = self.addtodo
        self.cmds['todo finish'] = self.removetodo
        self.todos = {}
        self.statefilename = "TODO"

    def gear(self):
        "TasksModule gear function"
        for todo in list(self.todos.keys()):
            #TODO Better way to check if it's past due.
            # Checks to see if the time string is "DUE!" rather than a valid
            #time.
            if self.todos[todo] == "DUE!":
                self.out("You missed a deadline! %s is overdue!" % todo)
                continue

            #TODO Why is this here?
            if self.todos[todo] == "None":
                continue

            #TODO Use datetime and make this comprehensible
            duetimestamp = time.mktime(self.todos[todo])
            duetime = datetime.datetime.fromtimestamp(duetimestamp)
            timeleft = duetime - datetime.datetime.now()

            if datetime.datetime.now() > duetime:
                self.todos[todo] = "DUE!"
                self.out("%s is due NOW!" % todo)
            elif timeleft.days <= 1:
                self.out("Todo '%s' is coming up soon! Due date: %s" %
                (todo, time. strftime("%B %d, %Y. %H:%M:00", self.todos[todo])))

    def save_state(self):
        """Saves state to a file with formats:
            Name
                or
            Name|DueDate"""
        f = file(self.statefilename, 'w')
        #TODO Better way to store state.

        for todo in list(self.todos.keys()):
            if not self.todos[todo] == "None":
                tstring = time.strftime("%B %d, %Y. %H:%M:00", self.todos[todo])
                f.write("%s|%s\n" % (todo, tstring))
            else:
                f.write("%s\n" % todo)
        f.close()

    def load_state(self):
        "Loads state from file."
        if not os.path.exists(self.statefilename):
            self.out("State file doesn't exist, clean slate.")
            return
        f = file(self.statefilename, 'r')

        for line in f.readlines():
            if not "|" in line:
                self.todos[line[:-1]] = "None"
            else:
                n = line[:line.index("|")]
                d = line[line.index("|") + 1:-1]
                self.todos[n] = time.strptime(d, "%B %d, %Y. %H:%M:00")

    ## Module-Specific Commands ##
    def addtodo(self):
        "Add a todo item to the list interactively."
        self.out("Name?")
        n = input("")
        b = ""
        while not b.lower() == "yes" and not b.lower() == "no":
            self.out("Due date? (Yes/no. Or cancel)")
            b = input("")
            if b.lower() == "cancel":
                self.out("Cancelling")
                return
        d = "None"
        t = "None"
        if b.lower() == "yes":
            #TODO Better way to input time.
            self.out("When? (format:'month date, year. hour:min' 24-hour time)")
            d = input("")
            try:
                t = time.strptime(d, "%B %d, %Y. %H:%M")
            except ValueError:
                self.out("Bad date format. Try again following the format.")
                return

        self.todos[n] = t
        if not d == "None":
            self.out("Added todo '%s' on '%s'" % (n, d))
        else:
            self.out("Added todo '%s' with no due date" % (n))

        self.save_state()

    def removetodo(self):
        "Removes an item from the todo list (Finishes)"
        self.out("Which one did you finish?")
        n = input("")

        if n in self.todos:
            del self.todos[n]
        self.out("Removed '%s' from todo list." % n)


class VoxModule(Module):
    """Vox Module
    Interface module for the bot.
    This module has access to most of the other modules in some way or another.
    It is intended as the main interface for the user.
    It has a special functionality with commands. Vox has a set of sub commands
    To start using sub commands, the user types "vox" at which point they are
    given another command prompt. The user can also use the format "vox command"
    for these commands."""

    def __init__(self, name, parent):
        "Vox Module init function"
        super(VoxModule, self).__init__(name=name, parent=parent)
        self.updatetime = 0

        self.cmds['vox'] = self.cmdinterface
        # The vox module has a set of subcommands. These commands are either
        #entered after typing 'vox' or in the same line in the format
        #'vox subcommand'
        self.subcmds = {
            "time": self.subtime,
            "nummodules": self.subrunning,
            "todo": self.subtodos,
            "reminders": self.subreminders,
            "help": self.subhelp
            }
        # Register all subcommands in format 'vox subcommand'
        for subcmd in list(self.subcmds.keys()):
            self.cmds["vox %s" % subcmd] = self.subcmds[subcmd]

    def run(self):
        "Vox main run function. Greets the user on start."
        # Greets the user depending on the time of day.
        t_hour = time.localtime(time.time()).tm_hour
        self.out("Hello!")
        if t_hour < 12:
            self.out("Good morning! Hope you slept well!")
        elif t_hour < 16:
            self.out("Good afternoon! Being productive today?")
        else:
            self.out("Good evening!")

        # Print out some help text for the user.
        self.out("Type 'cmds' or 'commands' to see all available commands.")
        self.out("Type 'quit' or 'q' to exit the program.")
        self.out("Call my name (Vox) to get my attention.")

    ############################
    # Module-Specific Commands #
    ############################
    def cmdinterface(self):
        """The main interface command. Runs when the user types 'vox.'
        The user can then enter sub commands for vox to perform."""
        # Runs when the user types 'vox'
        self.out("How may I help you? (Type 'help' for assistance)")
        cmdstring = input("")
        # Check to see if the user entered a valid command
        foundcmd = False
        for cmd in list(self.subcmds.keys()):
            if cmdstring.lower() == cmd:
                # If it is valid, execute it.
                self.subcmds[cmd]()
                foundcmd = True

        if not foundcmd:
            self.out("I'm sorry, I didn't understand that.")
            self.out("Ask me 'help' for a list of what I can understand.")

    ################
    # Sub-commands #
    ################
    def subtime(self):
        #TODO Make a 12-hour and 24-hour mode for the user to toggle
        "Sub command: Displays current time"
        self.out("It is currently %s. Or %s in 12-hour time" %
        (time.asctime(), time.strftime("%I:%M:%S %p")))

    def subhelp(self):
        "Sub command: Lists all sub commands"
        self.out("Here's what I can understand:")
        for cmd in list(self.subcmds.keys()):
            sys.stdout.write("    %s\n" % cmd)
        # Allow the user to input a vox command again now that they've seen the
        #list.
        self.cmdinterface()
        self.out("You can also preface one of these commands with my name.")

    def subrunning(self):
        #TODO Make it list them.
        "Sub command: Shows number of running modules"
        self.out("There are currently %i modules running" %
        threading.active_count())

    def subtodos(self):
        "Sub command: Interfaces with TasksModule (If present) and lists todos."
        # Check to see if the todo module is even installed and running
        foundmod = False
        for module in self.parent.modules:
            if module.name == "Todo":
                foundmod = True
                break

        if not foundmod:
            self.out("Sorry, it looks like the Todo module is not installed")
            return

        todos = module.get_todos()
        self.out("Here's your todo list:")
        i = 1
        for todo in list(todos.keys()):
            if todos[todo] == "DUE!":
                sys.stdout.write("    %i. %s, OVERDUE!\n" % (i, todo))
            elif todos[todo] != "None":
                sys.stdout.write("    %i. %s, due on %s\n" %
                (i, todo, time.strftime("%B %d, %Y. %H:%M:00", todos[todo])))
            else:
                sys.stdout.write("    %i. %s\n" % (i, todo))
            i += 1

    def subreminders(self):
        "Sub command: Lists all reminders if AlarmsModule is present."
        # Check to see if the reminders module is even installed and running
        foundmod = False
        for module in self.parent.modules:
            if module.name == "Reminders":
                foundmod = True
                break

        if not foundmod:
            self.out("Sorry, the Reminders module is not running right now.")
            return

        rems = module.reminders
        self.out("Sure thing, here are your currently active reminders:")
        for reminder in list(rems.keys()):
            sys.stdout.write("    %s - %s" % (reminder, rems[reminder]))


class Bot (object):
    """Main program class.
    Structured much like a threading.Thread class, but is not a subclass.

    Call the start() function to begin the bot. Call stop() to end the bot
    and all threads.
    Has a few built-in commands that work without any working modules.

    The run() function contains the mainloop for the main thread.
    add_module() can be called at any time to add another module instance
    to the but."""

    def __init__(self):
        "Main init function"
        self.done = True
        self.modules = []
        # Initialize with builtin commands:
        self.cmds = {
            'q': self.stop,
            'quit': self.stop,
            'cmds': self.listcmds,
            'commands': self.listcmds
            }

    def out(self, text):
        "Just like the modules, a way to uniformly output to the screen."
        sys.stdout.write(time.strftime("[%H:%M:%S] "))
        sys.stdout.write("[Main] ")
        sys.stdout.write(text)
        sys.stdout.write('\n')

    def start(self):
        """Entry point for the main class."""
        os.system(['clear', 'cls'][os.name == 'nt'])
        self.out("Starting bot at %s.\n" % time.asctime())
        self.done = False
        # Start all modules which were installed before the bot began
        for module in self.modules:
            self.out("Starting module %s" % module.name)
            try:
                module.start()
            except Exception as e:
                self.out("Error starting module %s." % module.name)
                self.out("Error text: '%s'" % e)
        self.run()

    def stop(self):
        """Ends all threads as quickly and gracefully as possible, then closes
        itself."""
        self.done = True
        self.out("Shutting down threads.")
        # Unlock all threads, forcing them to update now. They catch the fact
        #that their parent is done, and then end themselves, also saving their
        #states to a file for loading later.
        for thread in self.modules:
            thread.event.set()

        sys.stdout.write("\n")
        self.out("Ending bot at %s." % time.asctime())

    def listcmds(self):
        """Lists all CURRENTLY AVAILABLE commands.
        This includes commands added by running modules."""
        self.out("Listing commands")
        cmds = list(self.cmds.keys())
        cmds.sort()
        for cmd in cmds:
            sys.stdout.write("    %s" % cmd)

        self.out("What is your command?")

    #TODO Add a command list that only includes builtins

    def run(self):
        """Mainloop for the main thread.
        Deals with almost all user input."""
        try:
            while not self.done:
                #if cmdstring == "quit" or cmdstring == 'q':
                 #   self.stop()
                #TODO Do command input without input()
                cmdstring = None
                cmdstring = input("")

                #self.out("recieved command '%s'"%(cmdstring)) # For debugging
                if cmdstring.lower() in self.cmds:
                    self.cmds[cmdstring.lower()]()
        except KeyboardInterrupt:
            # Allow the bot to quit gracefully in the event of a
            #keyboardinterrupt. It might be wise to NOT do this.
            #TODO See if this is a good idea
            self.stop()

    def add_module(self, module):
        "Adds a module to the list of running modules and registers its cmds."
        self.modules.append(module)
        for cmd in list(module.cmds.keys()):
            self.cmds[cmd] = module.cmds[cmd]
        # If the bot is already running and the thread is being added later
        #otherwise let the main thread start this new module with all the others
        if not self.done:
            self.out("Adding module %s at %s" % (module.name, time.asctime()))
            module.start()

if __name__ == '__main__':
    bot = Bot()

    #TODO Make these not hard-coded. Either manually or parsed from a file
    bot.add_module(RemindersModule("Reminders", bot))
    bot.add_module(TasksModule("Todo", bot))

    # Always add vox last.
    bot.add_module(VoxModule("Vox", bot))

    bot.start()
