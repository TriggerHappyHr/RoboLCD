# -*- coding: utf-8 -*-
from kivy.uix.button import Button
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.togglebutton import ToggleButton
from .. import roboprinter
from functools import partial
from kivy.logger import Logger
from kivy.clock import Clock
from pconsole import pconsole
import thread
from Filament_Wizard import Filament_Wizard_Finish, Filament_Wizard_1_5, Filament_Wizard_2_5, Filament_Wizard_3_5, Filament_Wizard_4_5, Filament_Wizard_5_5
from z_offset_wizard import Z_Offset_Wizard_Finish, Z_Offset_Wizard_1_4, Z_Offset_Wizard_2_4, Z_Offset_Wizard_3_4, Z_Offset_Wizard_4_4
class WizardButton(Button):
    pass

class PreheatWizard(BoxLayout):
    """
     #WARNING: ONLY HANDLES SINGLE EXTRUDER

    PreheatWizard orchestrates all that is necessary to guide the user to preheat the extruder for his or her filament type, PLA or ABS.

    Trying a new implementation 9/20/16. This Wizard is implemented differently than the ZOffset Wizard. This object will have access to the screen manager object.

    Why: Testing whether this implementation is easier to understand and more maintainable than Zoffset Wizard implementation.

    What:
        The root object, RoboScreenManager, manages the ZOffset Wizard. This has led to a method, .generate_zaxis_wizard(), that encapsulates all functionality necessary to render the wizard. I find it hard to read and edit because it's a clump of functions defined within functions. It is written in this way to accomodate the mult-screen nature of the wizard.

        I decided to implement it in this manner to keep in line with the idea that RoboScreenManager is the screen manager. This means that RoboScreenManager holds all functionality as it pertains to rendering new screens. The wizards need to access this functionality to render screens for each step. I thought it might be more maintainable to keep that functionality defined within RoboScreenManager.

        This is an experiment to see what happens when we pass RoboScreenManager into other objects. As opposed to passing other objects into RoboScreenManager

    RoboScreenManager instantiates preheatwizard and then passes control over to it.
    """
    def __init__(self, roboscreenmanager, name, **kwargs):
        super(PreheatWizard, self).__init__(**kwargs)
        # first screen defined in .kv file
        self.sm = roboscreenmanager
        self.name = name #name of initial screen
        self.plastic_chosen = '' #title of second screen


    def second_screen(self, plastic_type):
        # Sets temperature
        # renders the second backbutton screen
        # Displays heating status and a button that sends you to mainscreen's printer status tab

        self.plastic_chosen = plastic_type.lower()
        if self.plastic_chosen == 'abs':
            self._preheat_abs()
        elif self.plastic_chosen == 'pla':
            self._preheat_pla()
        else:
            return

        c = self._second_screen_layout()

        self.sm._generate_backbutton_screen(name=self.name+'[1]', title=self.plastic_chosen.upper(), back_destination=self.name, content=c)

    def _second_screen_layout(self):
        layout = FloatLayout(size=(450,450))
        label = Label(
            font_size=40,
            pos_hint={'center_x': .5, 'top': 1.2}
            )
        if self.plastic_chosen == 'abs':
            t = u'Heating to 230°C'
        elif self.plastic_chosen == 'pla':
            t = u'Heating to 200°C'
        else:
            t = u'Error: plastic not registered'
        label.text = t
        b = Button(
            text='OK',
            pos_hint={'center_x': .5, 'y': 0},
            font_size=30,
            size_hint= [.5,.5],
            border=[40,40,40,40],
            background_normal="Icons/rounded_black.png"
        )
        b.bind(on_press=self._go_back_to_printer_status)

        layout.add_widget(label)
        layout.add_widget(b)
        return layout

    def _go_back_to_printer_status(self, *args, **kwargs):
        self.sm.go_back_to_main(tab='printer_status_tab')

    def _preheat_abs(self):
        # pre heat to 230 degrees celsius
        roboprinter.printer_instance._printer.set_temperature('tool0', 230.0)


    def _preheat_pla(self):
        # pre heat to 200 degrees celsius
        roboprinter.printer_instance._printer.set_temperature('tool0', 200.0)

class FilamentWizard(Widget):
    """ """
    temp = NumericProperty(0.0)
    layout2 = None
    extrude_event = None
    def __init__(self, loader_changer, robosm, name,  **kwargs):
        super(FilamentWizard, self).__init__(**kwargs)
        # first screen defined in .kv file
        self.sm = robosm
        self.name = name #name of initial screen
        self.first_screen(**kwargs)
        self.poll_temp() #populates self.temp
        self.load_or_change = loader_changer

    def first_screen(self, **kwargs):
        """
        First Screen:
            displays Start button that will open second_screen
        """
        layout = Filament_Wizard_1_5()
        layout.ids.start.fbind('on_press',self.second_screen)

        self.sm._generate_backbutton_screen(name=self.name, title=kwargs['title'], back_destination=kwargs['back_destination'], content=layout)

    def second_screen(self, *args):
        """
        the Heating Screen:
            Sets the temperature of the extruder to 230
            Display heating status to user
            Open third screen when temperature hits 230
        """
        #display heating status to user

        #end the event before starting it again
        if self.extrude_event != None:
            self.end_extrude_event()


        if self.load_or_change == 'CHANGE':
            _title = 'Filament Wizard 1/5'
        else:
            _title = 'Filament Wizard 1/4'

        self.layout2 = Filament_Wizard_2_5()
        
        this_screen = self.sm._generate_backbutton_screen(name=self.name+'[1]', title=_title, back_destination=self.name, content=self.layout2)
        #back_button will also stop the scheduled events: poll_temp and switch_to_third_screen
        this_screen.ids.back_button.bind(on_press=self.cancel_second_screen_events)

        # Heat up extruder
        roboprinter.printer_instance._printer.set_temperature('tool0', 230.0)
        self.tmp_event = Clock.schedule_interval(self.poll_temp, .5) #stored so we can stop them later
        self.s_event = Clock.schedule_interval(self.switch_to_third_screen, .75) #stored so we can stop them later

        

    ###Second screen helper functions ###
    def cancel_second_screen_events(self, *args):
        self.tmp_event.cancel()
        self.s_event.cancel()

    def update_temp_label(self, obj, *args):
        # updates the temperature for the user's view
        obj.text = str(self.temp) + "°C"

    def poll_temp(self, *args):
        # updates the temperature
        r = roboprinter.printer_instance._printer.get_current_temperatures()
        self.temp = r['tool0']['actual']
        Logger.info('Temp: {}'.format(self.temp))
        if self.layout2 != None:
            self.layout2.update_temp(self.temp)

    def switch_to_third_screen(self, *args):
        # switches to third screen when temperature >= 229.0
        if self.temp >= 229.0:
            if self.load_or_change == 'CHANGE':
                self.third_screen()
                # clock event no longer needed
                self.cancel_second_screen_events()
            elif self.load_or_change == 'LOAD':
                self.fourth_screen()
                # clock event no longer needed
                self.cancel_second_screen_events()
    #####################################

    def third_screen(self):
        """
        Pull filament Screen:
            Display instructions to user -- Pull out filament
            Display button that will open fourth screen
        """
        # roboprinter.printer_instance._printer.jog('e', -130.00)
        c = Filament_Wizard_3_5()
        c.ids.next_button.fbind('on_press',self.fourth_screen)
        this_screen = self.sm._generate_backbutton_screen(name=self.name+'[2]', title='Filament Wizard 2/5', back_destination=self.name, content=c)

        #end the event before starting it again
        if self.extrude_event != None:
            self.end_extrude_event()
        self.extrude_event = Clock.schedule_interval(self.retract, 1)
        

        # back_button deletes Second Screen, as back destination is first screen
        second_screen = self.sm.get_screen(self.name+'[1]')
        delete_second = partial(self.sm.remove_widget, second_screen)
        this_screen.ids.back_button.bind(on_press=delete_second)

    def fourth_screen(self, *args):
        """
        Load filament screen:
            Display instructions to user -- Load filament
            Display button that will open fifth screen
        """

        if self.load_or_change == 'CHANGE':
            _title = 'Filament Wizard 3/5'
            back_dest = self.name+'[2]'
        else:
            _title = 'Filament Wizard 2/4'
            back_dest = self.name

        if self.extrude_event != None:
            self.end_extrude_event()
        c = Filament_Wizard_4_5()
        c.ids.next_button.fbind('on_press', self.fifth_screen)
        self.sm._generate_backbutton_screen(name=self.name+'[3]', title=_title, back_destination=back_dest, content=c)

    def fifth_screen(self, *args):
        """
        Final screen / Confirm successful load:
            Extrude filament
            Display instruction to user -- Press okay when you see plastic extruding
            Display button that will move_to_main() AND stop extruding filament
        """
        if self.load_or_change == 'CHANGE':
            _title = 'Filament Wizard 4/5'
            back_dest = self.name+'[3]'
        else:
            _title = 'Filament Wizard 3/4'
            back_dest = self.name+'[3]'

        c = Filament_Wizard_5_5()
        c.ids.next_button.fbind('on_press', self.end_wizard)
        self.sm._generate_backbutton_screen(name=self.name+'[4]', title=_title, back_destination=back_dest, content=c)

        #end the event before starting it again
        if self.extrude_event != None:
            self.end_extrude_event()
        self.extrude_event = Clock.schedule_interval(self.extrude, 1)

    def extrude(self, *args):
        # wrapper that can accept the data pushed to it by Clock.schedule_interval when called
        roboprinter.printer_instance._printer.extrude(5.0)

    def retract(self, *args):
        roboprinter.printer_instance._printer.extrude(-5.0)

    def end_extrude_event(self, *args):
        self.extrude_event.cancel()

    def end_wizard(self, *args):
        self.extrude_event.cancel()
        c = Filament_Wizard_Finish()

        if self.load_or_change == 'CHANGE':
            _title = 'Filament Wizard 5/5'
            
        else:
            _title = 'Filament Wizard 4/4'
            

        self.sm._generate_backbutton_screen(name=self.name+'[5]', title=_title, back_destination=self.name+'[4]', content=c)


    def _generate_layout(self, l_text, btn_text, f):
        """
        Layouts are similar in fashion: Text and Call to Action button
        creates layout with text and button and  binds f to button
        """
        layout = BoxLayout(orientation='vertical')
        btn = Button(text=btn_text, font_size=30)
        l = Label(text=l_text, font_size=30)
        btn.bind(on_press=f)
        layout.add_widget(l)
        layout.add_widget(btn)
        return layout


class ZoffsetWizard(Widget):
    def __init__(self, robosm, back_destination, **kwargs):
        super(ZoffsetWizard, self).__init__()
        self.sm = robosm
        self.name = 'zoffset' #name of initial screen
        self.z_pos_init = 10.00
        self.z_pos_end = 0.0
        self.first_screen(back_destination=back_destination)

    def first_screen(self, **kwargs):
        
        c = Z_Offset_Wizard_1_4()
        c.ids.start.fbind('on_press', self.second_screen)

        self.sm._generate_backbutton_screen(name=self.name, title="Z Offset Wizard", back_destination=kwargs['back_destination'], content=c)

    def second_screen(self, *args):
        """Loading Screen
            Displays to user that Z Axis is moving """
        self._prepare_printer()

        title = "Z Offset 1/4"
        back_destination = self.name
        name = self.name + "[1]"

        layout = Z_Offset_Wizard_2_4()
        self.counter = 0
        Clock.schedule_interval(self.position_callback, 1)

        self.sm._generate_backbutton_screen(name=name, title=title, back_destination=back_destination, content=layout)
        Logger.info("2nd Screen: RENDERED")
        # self.third_screen()

    def third_screen(self, *args):
        """
        Instructions screen
        """
        title = "Z Offset 2/4"
        name = self.name + "[2]"
        back_destination = self.name

        layout = Z_Offset_Wizard_3_4()
        layout.ids.done.fbind('on_press', self.fourth_screen)

        this_screen = self.sm._generate_backbutton_screen(title=title, name=name, back_destination=back_destination, content=layout)

        # # back_button deletes Second Screen, as back destination is first screen
        # second_screen = self.sm.get_screen(self.name)
        # delete_second = partial(self.sm.remove_widget, second_screen)
        # this_screen.ids.back_button.bind(on_press=delete_second)

    def fourth_screen(self, *args):
        """
        Z offset screen-- user interacts with the printer
        """
        title = "Z Offset 3/4"
        name = self.name + "[3]"
        back_destination = self.name + "[2]"

       
        layout = Z_Offset_Wizard_4_4()

        self.sm._generate_backbutton_screen(
            name=name,
            title=title,
            back_destination=back_destination,
            content=layout
        )

        self.z_pos_end = float(self._capture_zpos()[2]) #schema: (x_pos, y_pos, z_pos)
        self.z_pos_end = float(self._capture_zpos()[2]) #runs twice because the first call returns the old position
        Logger.info("ZCapture: z_pos_end {}".format(self.z_pos_end))
        self.counter = 0
        Clock.schedule_interval(self.z_capture_callback, .5)

    def fifth_screen(self, *args):
        title = "Z Offset 4/4"
        name = self.name + "[4]"
        back_destination = self.name + "[3]"

        layout = Z_Offset_Wizard_Finish()
        self.zoffset = self.z_pos_end - self.z_pos_init
        layout.z_value = self.zoffset
        layout.ids.save.fbind('on_press', self._save_zoffset )
        layout.ids.save.fbind('on_press', self._end_wizard )

        self.sm._generate_backbutton_screen(
            name=name,
            title=title,
            back_destination=back_destination,
            content=layout
        )


    #####Helper Functions#######
    def _prepare_printer(self):
        # Prepare printer for zoffset configuration
        roboprinter.printer_instance._printer.commands(['M851 Z-10', 'M500', 'G90'])
        roboprinter.printer_instance._printer.commands(['G28', 'G91', 'G1 X5 Y30 F800', 'G90' ])
        

    def position_callback(self, dt):
        pos = pconsole.get_position()
        xpos = int(float(pos[0]))
        ypos = int(float(pos[1]))
        zpos = int(float(pos[2]))
        if self.counter > 3 and  xpos == 71.00 and ypos == 62.00 and zpos == 10:
            if self.sm.current == 'zoffset[1]':
                Logger.info('Succesfully found position')
                self.third_screen()
                return False
            else:
                Logger.info('User went to a different screen Unscheduling self.')
                return False
        self.counter += 1
        if self.counter > 30:
            if self.sm.current == 'zoffset[1]':
                Logger.info('could not find position, but continuing anyway')
                self.third_screen()
                return False
            else:
                Logger.info('User went to a different screen Unscheduling self.')
                return False

    def z_capture_callback(self, dt):
        self.counter += 1
        if self.counter > 2:
            self.fifth_screen()
            return False

    def _capture_zpos(self):
        Logger.info("ZCapture: Init")
        p = pconsole.get_position()
        Logger.info("ZCapture: {}".format(p))
        return p

    def _save_zoffset(self, *args):
        write_zoffset = 'M851 Z{}'.format(self.zoffset)
        save_to_eeprom = 'M500'
        roboprinter.printer_instance._printer.commands([write_zoffset, save_to_eeprom])
        
    def _end_wizard(self, *args):
        roboprinter.printer_instance._printer.commands('G1 Z160 F1500')
        self.sm.go_back_to_main()



    ###############################



#Buttons

class Z_Offset_Wizard_Button(Button):
    pass
class Filament_Loading_Wizard_Button(Button):
    pass
class Filament_Change_Wizard_Button(Button):
    pass