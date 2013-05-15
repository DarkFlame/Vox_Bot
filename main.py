import sys
import os
import time
import datetime
import threading

#import mechanize


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
        self.updatetime = 0.

        self.cmds = {}

        self.event = threading.Event()

    def run(self):
        """This function is run when the main thread calls the start() function
        from threading.Thread.
        It loads the state (If possible), then starts the mainloop."""
        self.load_state()
        while not self.parent.done:
            try:
                self.gear()
            except Exception as e:
                sys.stderr.write("ERROR in thread %s. Error message: '%s'" %
                    (self.name, e))
                sys.stderr.write("backing up state and exiting.")
                self.parent.done = True
                return

            # time.sleep(self.updatetime)
            interrupted = self.event.wait(self.updatetime)
            # If the thread was interrupted, not timed out
            if interrupted:
                self.save_state()
                return
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
class AlarmModule(Module):
    """Alarms module
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
        "AlarmModule __init__ function."
        super(AlarmModule, self).__init__(name=name, parent=parent)
        self.alarms = {}
        self.updatetime = 5.

        self.cmds['reminders add'] = self.addreminder
        self.cmds['reminders list'] = self.listreminders
        self.statefilename = "REMINDERS"

    def gear(self):
        "AlarmModule gear function."
        for al in list(self.alarms.keys()):
            tmstring = self.alarms[al]
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
            #TODO Error here with time format
            tstring = time.strftime("%B %d, %Y. %H:%M:00",
                self.alarms[reminder])
            f.write("%s|%s\n" % (reminder, tstring))
        f.close()

    def load_state(self):
        "Loads reminders from a file, if it exists."
        if not os.path.exists(self.statefilename):
            self.out("State file doesn't exist, clean slate.")
            return
        f = file(self.statefilename, 'r')
        for line in f.readlines():
            n = line[:line.index("|")]
            d = line[line.index("|") + 1:-1]
            self.reminders[n] = time.strptime(d, "%B %d, %Y. %H:%M:00")

    def add_alarm(self, name, time):
        "Adds alarm to self.alarms."
        self.alarms[name] = time
        self.out("Alarm '%s' added at %s." % (name, time))
        self.save_state()

    ## Module-Specific Commands ##
    def addreminder(self):
        """Adds a reminder to the existing ones.
        Asks for a name and then the time.
        If the user inputs a bad time format, it cancels and the user has to
        start over."""
        #TODO use datetime
        self.out("Adding reminder...")
        n = raw_input("Name?\n")
        t = raw_input("Time? ('hr:mn')\n")
        if not ":" in t:
            self.out("Bad time format ('hr:mn')")
            return
        try:
            int(t[:t.index(":")])
            int(t[t.index(":") + 1:])
        except ValueError:
            self.out("Bad time format ('hr:mn')")
            return
        self.add_alarm(n, t)

    def listreminders(self):
        'Prints out each reminder in the format "Name - Time"'
        self.out("Listing alarms...")
        for al in list(self.alarms.keys()):
            sys.stdout.write("    %s - %s\n" % (al, self.alarms[al]))


class TodoModule(Module):
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
        "TodoModule __init__ function"
        super(TodoModule, self).__init__(name=name, parent=parent)
        # self.updatetime = 60*60 # 60 seconds times 60 minutes = 1 hour.
        self.updatetime = 30 * 60  # 60 seconds times 30 minutes = 1 hour.

        self.cmds['todo add'] = self.addtodo
        self.cmds['todo finish'] = self.removetodo
        self.todos = {}
        self.statefilename = "TODO"

    def gear(self):
        "TodoModule gear function"
        for todo in list(self.todos.keys()):
            if self.todos[todo] == "DUE!":
                self.out("You missed a deadline! %s is overdue!" % todo)
                continue

            if self.todos[todo] == "None":
                continue

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
        n = raw_input("")
        b = ""
        while not b.lower() == "yes" and not b.lower() == "no":
            self.out("Due date? (Yes/no. Or cancel)")
            b = raw_input("")
            if b.lower() == "cancel":
                self.out("Cancelling")
                return
        d = "None"
        t = "None"
        if b.lower() == "yes":
            self.out("When? (format:'month date, year. hour:min' 24-hour time)")
            d = raw_input("")
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
        n = raw_input("")

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
        super(VoxModule, self).__init__(name=name, parent=parent)
        self.updatetime = 0

        self.cmds['vox'] = self.cmdinterface
        self.subcmds = {
            "time": self.subtime,
            "nummodules": self.subrunning,
            "todo": self.subtodos,
            "reminders": self.subreminders,
            "help": self.subhelp
            }
        for subcmd in list(self.subcmds.keys()):
            self.cmds["vox %s" % subcmd] = self.subcmds[subcmd]

    def run(self):
        t_hour = time.localtime(time.time()).tm_hour
        self.out("Hello!")
        if t_hour < 12:
            self.out("Good morning! Hope you slept well!")
        elif t_hour < 16:
            self.out("Good afternoon! Being productive today?")
        else:
            self.out("Good evening!")

        self.out("Type 'cmds' or 'commands' to see all available commands.")
        self.out("Type 'quit' or 'q' to exit the program.")
        self.out("Call my name (Vox) to get my attention.")

    ## Module-Specific Commands ##
    def cmdinterface(self):
        # Runs when the user types 'vox'
        self.out("How may I help you? (Type 'help' for assistance)")
        cmdstring = raw_input("")
        foundcmd = False
        for cmd in list(self.subcmds.keys()):
            if cmdstring.lower() == cmd:
                self.subcmds[cmd]()
                foundcmd = True

        if not foundcmd:
            self.out("I'm sorry, I didn't understand that.")
            self.out("Ask me 'help' for a list of what I can understand.")

    ## Sub-commands ##
    def subtime(self):
        self.out("It is currently %s. Or %s in 12-hour time" %
        (time.asctime(), time.strftime("%I:%M:%S %p")))

    def subhelp(self):
        self.out("Here's what I can understand:")
        for cmd in list(self.subcmds.keys()):
            sys.stdout.write("%s\n" % cmd)
        self.interface()
        self.out("You can also preface one of these commands with my name.")

    def subrunning(self):
        self.out("There are currently %i modules running" %
        threading.active_count())

    def subtodos(self):
        foundmod = False
        for module in self.parent.modules:
            if module.name == "Todo":
                foundmod = True
                break

        if not foundmod:
            self.out("Sorry, it looks like the Todo module is not installed")

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
        foundmod = False
        for module in self.parent.modules:
            if module.name == "Reminders":
                foundmod = True
                break

        if not foundmod:
            self.out("Sorry, the Reminders module is not running right now.")
            return

        rems = module.get_reminders()
        self.out("Sure thing, here are your currently active reminders:")
        for reminder in rems.iterkeys():
            sys.stdout.write("    %s - %s" % (reminder, rems[reminder]))


class Bot (object):

    def __init__(self):
        self.done = True
        self.modules = []
        self.cmds = {
            'q': self.stop,
            'quit': self.stop,
            'cmds': self.listcmds,
            'commands': self.listcmds}

    def out(self, text):
        sys.stdout.write(time.strftime("[%H:%M:%S] "))
        sys.stdout.write("[Main] ")
        sys.stdout.write(text)
        sys.stdout.write('\n')

    def start(self):
        os.system(['clear', 'cls'][os.name == 'nt'])
        self.out("Starting bot at %s.\n" % time.asctime())
        self.done = False
        for module in self.modules:
            self.out("Starting module %s" % module.name)
            module.start()
        self.run()

    def stop(self):
        self.out("Shutting down threads.")
        for thread in self.modules:
            thread.event.set()
        self.done = True
        print
        self.out("Ending bot at %s." % time.asctime())

    def listcmds(self):
        self.out("Listing commands")
        cmds = self.cmds.keys()
        cmds.sort()
        for cmd in cmds:
            print cmd

        self.out("What is your command?")

    def run(self):
        try:
            while not self.done:
                cmdstring = None
                cmdstring = raw_input("")

                #self.out("recieved command '%s'"%(cmdstring))
                for cmd in self.cmds.iterkeys():
                    if cmdstring.lower() == cmd:
                        self.cmds[cmd]()
                #if cmdstring == "quit" or cmdstring == 'q':
                 #   self.stop()
        except KeyboardInterrupt:
            self.stop()

    def add_module(self, module):
        self.modules.append(module)
        for cmd in module.cmds.iterkeys():
            self.cmds[cmd] = module.cmds[cmd]
        # If the bot is already running and the thread is being added later
        if not self.done:
            self.out("Adding module!")
            module.start()

if __name__ == '__main__':
    bot = Bot()
    alarms = AlarmModule("Reminders", bot)
    bot.add_module(alarms)
    todo = TodoModule("Todo", bot)
    bot.add_module(todo)

    # Always start vox last.
    greeter = VoxModule("Vox", bot)
    bot.add_module(greeter)
    print "starting bot"
    bot.start()
