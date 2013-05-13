import sys,os,time,datetime
import threading

import mechanize
        
class Module(threading.Thread):

    def __init__(self, name, parent):
        super(Module, self).__init__(name=name)
        self.name = name
    
        self.parent = parent
        self.updatetime = 0.
        
        self.cmds = {}
        
        self.event = threading.Event()
            
    def run(self):
        self.load_state()
        while not self.parent.done:
            try:
                self.gear()
            except Exception, e:
                sys.stderr.write("""\n
\n=======================================================
ERROR
in thread %s.
Backing up state and exiting.
Error message: '%s'
WARNING THE BOT WILL LIKELY BE UNSTABLE
ADVISE QUITTING
=======================================================\n\n"""%(self.name,e))
                self.parent.done = True
                return
            
            # time.sleep(self.updatetime)
            interrupted = self.event.wait(self.updatetime)
            # If the thread was interrupted, not timed out
            if interrupted:
                self.save_state()
                return
        self.save_state()
                
    def save_state(self):
        pass
        
    def load_state(self):
        pass
        
    def gear(self):
        pass
        
    def out(self,message):
        sys.stdout.write(time.strftime("[%H:%M:%S] "))
        sys.stdout.write("[%s] "%self.name)
        sys.stdout.write(str(message))
        sys.stdout.write('\n')
        
class AlarmModule(Module):

    def __init__(self,name,parent):
        super(AlarmModule, self).__init__(name=name,parent=parent)
        self.alarms = {}
        self.updatetime = 5.
        
        self.cmds['reminders add'] = self.addreminder
        self.cmds['reminders list'] = self.listreminders
        self.statefilename = "REMINDERS"
        
    def gear(self):
        for al in self.alarms.iterkeys():
            tmstring = self.alarms[al]
            hr = int(tmstring[:tmstring.index(":")])
            mn = int(tmstring[tmstring.index(":")+1:])
            
            t = time.localtime(time.time())
            if t.tm_hour == hr:
                if t.tm_min == mn:
                    self.out("====%s!===="%al)
                    del self.alarms[al]
                    
    def save_state(self):
        f = file(self.statefilename,'w')
        
        for reminder in self.alarms.iterkeys():
            tstring = time.strftime("%B %d, %Y. %H:%M:00",self.alarms[reminder])
            f.write("%s|%s\n"%(reminder,tstring))
        f.close()
        
    def load_state(self):
        if not os.path.exists(self.statefilename):
            self.out("State file doesn't exist, clean slate.")
            return
        f = file(self.statefilename,'r')
        for line in f.readlines():
            n = line[:line.index("|")]
            d = line[line.index("|")+1:-1]
            self.reminders[n] = time.strptime(d, "%B %d, %Y. %H:%M:00")
                    
    def add_alarm(self, name, time):
        self.alarms[name]=time
        self.out("Alarm '%s' added at %s."%(name,time))
        self.save_state()
        
    def get_reminders(self):
        return self.alarms
        
    # Commands    
    def addreminder(self):
        #TODO use datetime
        self.out("Adding reminder...")
        n = raw_input("Name?\n")
        t = raw_input("Time? ('hr:mn')\n")
        if not ":" in t:
            self.out("Bad time format ('hr:mn')")
            return
        try:
            int(t[:t.index(":")])
            int(t[t.index(":")+1:])
        except ValueError:
            self.out("Bad time format ('hr:mn')")
            return
        self.add_alarm(n,t)
    
    def listreminders(self):
        self.out("Listing alarms...")
        for al in self.alarms.iterkeys():
            print "%s - %s"%(al,self.alarms[al])
            
class TodoModule(Module):

    def __init__(self,name,parent):
        super(TodoModule,self).__init__(name=name,parent=parent)
        # self.updatetime = 60*60 # 60 seconds times 60 minutes = 1 hour.
        self.updatetime = 30*60 # 60 seconds times 30 minutes = 1 hour.
        
        self.cmds['todo add'] = self.addtodo
        self.cmds['todo finish'] = self.removetodo
        self.todos = {}
        self.statefilename = "TODO"
        
    def gear(self):
        # Pesters the user about approaching deadlines and overdue items.
        for todo in self.todos.iterkeys():
            if self.todos[todo] == "DUE!":
                self.out("You missed a deadline! %s is overdue!"%todo)
                continue
                
            if self.todos[todo] == "None":
                continue
                
            duetime = time.mktime(self.todos[todo])
            timeleft = datetime.datetime.fromtimestamp(duetime) - datetime.datetime.now()
            if datetime.datetime.now() > datetime.datetime.fromtimestamp(duetime):
                self.todos[todo] = "DUE!"
                self.out("%s is due NOW!"%todo)
            elif timeleft.days <= 1:
                self.out("Todo '%s' is coming up soon! Due date: %s"%(todo,time.strftime("%B %d, %Y. %H:%M:00",self.todos[todo])))
    
    def get_todos(self):
        return self.todos
        
    def save_state(self):
        f = file(self.statefilename,'w')
        
        for todo in self.todos.iterkeys():
            if not self.todos[todo] == "None":
                tstring = time.strftime("%B %d, %Y. %H:%M:00",self.todos[todo])
                f.write("%s|%s\n"%(todo,tstring))
            else:
                f.write("%s\n"%todo)
        f.close()
        
    def load_state(self):
        if not os.path.exists(self.statefilename):
            self.out("State file doesn't exist, clean slate.")
            return
        f = file(self.statefilename,'r')
        
        for line in f.readlines():
            if not "|" in line:
                self.todos[line[:-1]] = "None"
            else:
                n = line[:line.index("|")]
                d = line[line.index("|")+1:-1]
                self.todos[n] = time.strptime(d, "%B %d, %Y. %H:%M:00")
    
    # Commands
    def addtodo(self):
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
            self.out("Added todo '%s' on '%s'"%(n,d))
        else:
            self.out("Added todo '%s' with no due date"%(n))
            
        self.save_state()
            
    def removetodo(self):
        self.out("Which one did you finish?")
        n = raw_input("")
        
        if n in self.todos:
            del self.todos[n]
        self.out("Removed '%s' from todo list."%n)
        
class VoxModule(Module):

    def __init__(self,name,parent):
        super(VoxModule,self).__init__(name=name,parent=parent)
        self.updatetime = 0
        
        self.cmds['vox'] = self.interface
        self.subcmds = {
            "time":self.subtime,
            "nummodules":self.subrunning,
            "todo":self.subtodos,
            "reminders":self.subreminders,
            "help":self.subhelp
            }
        for subcmd in self.subcmds.iterkeys():
            self.cmds["vox %s"%subcmd] = self.subcmds[subcmd]
    
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
    
    # Commands
    def interface(self):
        # Runs when the user types 'vox'
        self.out("How may I help you? (Type 'help' for assistance)")
        cmdstring = raw_input("")
        foundcmd = False
        for cmd in self.subcmds.keys():
            if cmdstring.lower() == cmd:
                self.subcmds[cmd]()
                foundcmd = True
        
        if not foundcmd:
            self.out("I'm sorry, I didn't understand that. Ask me 'help' for a list of what I can understand.")
    
    # Sub-commands
    def subtime(self):
        self.out("It is currently %s. Or %s in 12-hour time"%(time.asctime(), time.strftime("%I:%M:%S %p")))
        
    def subhelp(self):
        self.out("Here's what I can understand:")
        for cmd in self.subcmds.keys():
            print cmd
        self.interface()
        self.out("You can also preface one of these commands with my name, as in 'Vox Help'")
        
    def subrunning(self):
        self.out("There are currently %i modules running"%threading.active_count())
        
    def subtodos(self):
        foundmod = False
        for module in self.parent.modules:
            if module.name == "Todo":
                foundmod = True
                break
                
        if foundmod == False:
            self.out("Sorry, it looks like the Todo module is not installed")
        
        todos = module.get_todos()
        self.out("Here's your todo list:")
        i = 1
        for todo in todos.iterkeys():
            if todos[todo] == "DUE!":
                print "    %i. %s, OVERDUE!"%(i,todo)
            elif todos[todo] != "None":
                print "    %i. %s, due on %s"%(i,todo,time.strftime("%B %d, %Y. %H:%M:00",todos[todo]))
            else:
                print "    %i. %s"%(i,todo)
            i+=1
        
    def subreminders(self):
        foundmod = False
        for module in self.parent.modules:
            if module.name == "Reminders":
                foundmod = True
                break
                
        if foundmod == False:
            self.out("Sorry, the Reminders module is not running right now.")
            return
        
        rems = module.get_reminders()
        self.out("Sure thing, here are your currently active reminders:")
        for reminder in rems.iterkeys():
            print "    %s - %s"%(reminder, rems[reminder])
        

class Bot (object):

    def __init__(self):
        self.done = True
        self.modules = []
        self.cmds = {'q':self.stop,'quit':self.stop,'cmds':self.listcmds,'commands':self.listcmds}
        
    def out(self,text):
        sys.stdout.write(time.strftime("[%H:%M:%S] "))
        sys.stdout.write("[Main] ")
        sys.stdout.write(text)
        sys.stdout.write('\n')
        
    def start(self):
        os.system(['clear','cls'][os.name == 'nt'])
        self.out("Starting bot at %s.\n"%time.asctime())
        self.done = False
        for module in self.modules:
            self.out("Starting module %s"%module.name)
            module.start()
        self.run()
        
    def stop(self):
        self.out("Shutting down threads.")
        for thread in self.modules:
            thread.event.set()
        self.done = True
        print
        self.out("Ending bot at %s."%time.asctime())
        
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
        
    def add_module(self,module):
        self.modules.append(module)
        for cmd in module.cmds.iterkeys():
            self.cmds[cmd] = module.cmds[cmd]
        if not self.done: # If the bot is already running and the thread is being added later
            self.out("Adding module!")
            module.start()
        
if __name__ == '__main__':
    bot = Bot()
    alarms = AlarmModule("Reminders",bot)
    bot.add_module(alarms)
    todo = TodoModule("Todo",bot)
    bot.add_module(todo)
    
    # Always start vox last.
    greeter = VoxModule("Vox",bot)
    bot.add_module(greeter)
    print "starting bot"
    bot.start()
