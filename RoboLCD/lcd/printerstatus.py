# coding=utf-8
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.tabbedpanel import TabbedPanelHeader
from kivy.properties import NumericProperty, StringProperty, ObjectProperty
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.logger import Logger
from kivy.clock import Clock
from kivy.uix.modalview import ModalView
from .. import roboprinter
from connection_popup import Zoffset_Warning_Popup
import math


class PrinterStatusTab(TabbedPanelHeader):
    """
    Represents the Printer Status tab header and dynamic content
    """
    pass


class PrinterStatusContent(GridLayout):
    """
    """

    filename = StringProperty("")
    status = StringProperty("[ref=status][/ref]")
    extruder_one_temp = NumericProperty(0)
    extruder_one_max_temp = NumericProperty(200)
    extruder_two_max_temp = NumericProperty(200)
    extruder_two_temp = NumericProperty(0)
    bed_max_temp = NumericProperty(200)
    bed_temp = NumericProperty(0)
    progress = StringProperty('')

    def update(self, dt):
        temps = roboprinter.printer_instance._printer.get_current_temperatures()
        current_data = roboprinter.printer_instance._printer.get_current_data()
        filename = current_data['job']['file']['name']
        is_operational = current_data['state']['flags']['operational']
        is_ready = current_data['state']['flags']['ready']
        is_printing = current_data['state']['flags']['printing']
        is_paused = current_data['state']['flags']['paused']
        progress = current_data['progress']['completion']
        status = current_data['state']['text']
        #TODO: REFACTOR because the following variable assignments WILL fail when we starting implementing lcd_large.kv since these widgets wont exists for that iteration
        left_of_extruder = self.ids.left_of_extruder_status
        right_of_extruder = self.ids.right_of_extruder_status
        e_children = left_of_extruder.children + right_of_extruder.children

        self.filename = filename.replace('.gcode','') if filename else 'No File Loaded'

        if is_printing or is_paused:
            p_transformed = int(progress)
            self.progress = '[size=50]{}%[/size]'.format(p_transformed)
        else:
            self.progress = ''

        if progress == 100:
            roboprinter.printer_instance._printer.unselect_file()

        if 'tool0' in temps.keys():
            self.extruder_one_temp = temps['tool0']['actual']
            self.extruder_one_max_temp = temps['tool0']['target']
        else:
            self.extruder_one_temp = 0
            self.extruder_one_max_temp = 0

        if 'bed' in temps.keys():
            self.bed_temp = temps['bed']['actual']
            self.bed_max_temp = temps['bed']['target']
        else:
            self.bed_temp = 0
            self.bed_max_temp = 0

        if 'tool1' in temps.keys():
            self.extruder_two_temp = temps['tool1']['actual']
            self.extruder_two_max_temp = temps['tool1']['target']
        else:
            self.extruder_two_temp = 0
            self.extruder_two_max_temp = 0

        if is_printing and len(e_children) == 0:
            left_of_extruder.add_widget(StartPauseButton())
            right_of_extruder.add_widget(CancelButton())
        elif len(e_children) > 0 and not is_printing and not is_paused:
            left_of_extruder.clear_widgets()
            right_of_extruder.clear_widgets()

    def start_print(self):
        roboprinter.printer_instance._printer.start_print()
       

class StartPauseButton(Button):
    subtract_amount =  NumericProperty(40)
    def __init__(self, **kwargs):
        super(StartPauseButton, self).__init__(**kwargs)
        Clock.schedule_interval(self.sync_with_devices, .1)
        Clock.schedule_interval(self.colors, .1)

    def toggle_pause_print(self):
        roboprinter.printer_instance._printer.toggle_pause_print()


    def sync_with_devices(self, dt):
        '''makes sure that button's state syncs up with the commands that other devices push to the printer '''
        is_paused = roboprinter.printer_instance._printer.is_paused()
        if is_paused and self.ids.stopgo_label.text ==  '[size=30]Pause[/size]':
            self.ids.stopgo_label.text =  '[size=30]Resume[/size]'
            self.ids.stopgo_icon.source = 'Icons/Manual_Control/start_button_icon.png'
            self.subtract_amount = 50
        elif not is_paused and self.ids.stopgo_label.text ==  '[size=30]Resume[/size]':
            self.ids.stopgo_label.text =  '[size=30]Pause[/size]'
            self.ids.stopgo_icon.source = 'Icons/Manual_Control/stop_button_icon.png'
            self.subtract_amount =  40

    def colors(self, dt):
        '''updates the color  of the button based on Start or Pause state. Green for Start'''
        is_paused = roboprinter.printer_instance._printer.is_paused()
        if is_paused:
            self.background_normal = 'Icons/green_button_style.png'

        else:
            self.background_normal = 'Icons/blue_button_style.png'

class CancelButton(Button):
    def cancel_print(self, *args):
        if self.is_printing() or roboprinter.printer_instance._printer.is_paused() == True:
            roboprinter.printer_instance._printer.cancel_print()
            Logger.info('Cancellation: Successful')
            roboprinter.printer_instance._printer.unselect_file()
            Logger.info('Unselect: Successful')
    def no_button(self, instance):
        pass
    def modal_view(self):
        mv = ModalPopup()
        mv.ids.yes_button.bind(on_press = self.cancel_print)
        mv.ids.no_button.bind(on_press = self.no_button)
        mv.open()

    def is_printing(self):
        """ whether the printer is currently operational and ready for a new print job"""
        printing = roboprinter.printer_instance._printer.is_printing()
        if not printing:
            return False
        else:
            return True

class ModalPopup(ModalView):
    def cancellation_feedback(self):
        self.ids.modal_question.text = "Cancelling..."

    def dismiss_popup(self, *args):
        self.cancellation_feedback()
        self.dismiss()
        Logger.info('Dismiss Popup: Successful')
