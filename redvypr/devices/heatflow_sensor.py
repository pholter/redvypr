"""

Configuration options for a heatflow device

.. code-block::

- deviceconfig:
    name: heatflow1
    config:
      coeffs:
        - name: HFSV
          coeff: [2, 0, 9200, 0, 0, W/m2]
  devicemodulename: heatflow_sensor

"""

import datetime
import logging
import queue
from PyQt5 import QtWidgets, QtCore, QtGui
import time
import numpy as np
import logging
import sys
import yaml
import pyqtgraph

description = 'Parses and displays data of digital heat flow sensors with NMEA type data string'

pyqtgraph.setConfigOption('background', 'w')
pyqtgraph.setConfigOption('foreground', 'k')

logging.basicConfig(stream=sys.stderr)
logger = logging.getLogger('plot')
logger.setLevel(logging.DEBUG)

class datadisplay(QtWidgets.QWidget):
    """ A class that displays a number together with a title
    """
    def __init__(self,title=''):
        super(QtWidgets.QWidget, self).__init__()
        layout        = QtWidgets.QVBoxLayout(self)
        self.titlestr = title
        self.title    = QtWidgets.QLabel(self.titlestr)
        self.data     = QtWidgets.QLabel('no data')
        fsize         = self.data.fontMetrics().size(0, self.data.text())
        self.data.setFont(QtGui.QFont('Arial', fsize.height()+10))
        layout.addWidget(self.title)
        layout.addWidget(self.data)

    def set_data(self,data):
        newdatastr = "{:.6f}".format(data) # TODO, here a format string defined in the widget could be applied
        self.data.setText(newdatastr)
  
        


def parse_nmea(data):
    """ Parses a NMEA type heatflow data string
    $noSN,00000315.1035,HFS,-0.000196,V,-0.000392,W/m2,NTC,+0.028857,V,+33.926881,degC,VIN,+0.114332,V,+1.257654,VCC
    """

    datas = data.split(',')
    datadict = {}
    datadict['sn']       = datas[0][1:] # Serialnumber
    datadict['ts']       = float(datas[1]) # Sampling counter [s]
    datadict['hfname']   = datas[2] # Name of the sensor
    datadict['hfV']      = float(datas[3]) # Voltage 
    datadict['hfV_unit'] = datas[4] # Voltage Unit
    datadict['hf']       = float(datas[5]) # Heat flow 
    datadict['hf_unit']  = datas[6] # Heat flow Unit
    datadict['NTCname']  = datas[7] # Name of the sensor    
    datadict['NTCV']     = float(datas[8]) # Voltage 
    datadict['NTCV_unit']= datas[9] # Voltage Unit
    datadict['NTC']      = float(datas[10]) # Heat flow 
    datadict['NTC_unit'] = datas[11] # Heat flow Unit
    datadict['VINname']  = datas[12] # Name of the sensor    
    datadict['VINV']     = float(datas[13]) # Voltage 
    datadict['VINV_unit']= datas[14] # Voltage Unit
    datadict['VIN']      = float(datas[15]) # Heat flow 
    datadict['VIN_unit'] = datas[16] # Heat flow Unit

    return datadict


def convert_data_with_coeffs(data,coeffs):
    for coeff in coeffs:
        if(coeff['name'] in data):
            origdata = data[coeff['name']]
            if(coeff['coeff'][0] == 2): # Polynom
                convdata = coeff['coeff'][1] + origdata * coeff['coeff'][2] + origdata**2 * coeff['coeff'][3] + origdata**3 * coeff['coeff'][4]
            else:
                convdata = np.NaN

            data[coeff['convname']] = convdata

    return data

def start(datainqueue,dataqueue,comqueue,devicename,config={}):
    funcname = __name__ + '.start()'        
    while True:
        try:
            com = comqueue.get(block=False)
            print('received',com)
            break
        except:
            pass


        time.sleep(0.05)
        while(datainqueue.empty() == False):
            try:
                data = datainqueue.get(block=False)
                datap = parse_nmea(data['nmea'])
                # Check if we have coefficients to calculate values
                if('coeffs' in config.keys()):
                    datap = convert_data_with_coeffs(datap,config['coeffs'])
                    #print(datap)
                    
                datan = {**data, **datap} # Python 3.9: z = x | y
                datan['device'] = devicename
                dataqueue.put(datan)

            except Exception as e:
                logger.debug(funcname + ':Exception:' + str(e))            

class Device():
    def __init__(self,dataqueue=None,comqueue=None,datainqueue=None,config = {}):
        """
        """
        self.publish     = True # publishes data, a typical device is doing this
        self.subscribe   = True  # subscribing data, a typical datalogger is doing this
        self.datainqueue = datainqueue
        self.dataqueue   = dataqueue        
        self.comqueue    = comqueue
        self.config      = config # Please note that this is typically a placeholder, the config structure will be written by redvypr and the yaml
        self.name        = 'heatflowsensor' # This will be overwritten by the config!
                
    def start(self):
        start(self.datainqueue,self.dataqueue,self.comqueue,devicename=self.name,config=self.config)
        
    def __str__(self):
        sstr = 'heatflow_sensor'
        return sstr



class initDeviceWidget(QtWidgets.QWidget):
    device_start = QtCore.pyqtSignal(Device) # Signal requesting a start of the device (starting the thread)
    device_stop  = QtCore.pyqtSignal(Device) # Signal requesting a stop of device
    connect      = QtCore.pyqtSignal(Device) # Signal requesting a connect of the datainqueue with available dataoutqueues of other devices
    def __init__(self,device=None):
        super(QtWidgets.QWidget, self).__init__()
        layout        = QtWidgets.QFormLayout(self)
        self.device   = device
        self.label    = QtWidgets.QLabel("Heatflowsensor setup")
        self.conbtn = QtWidgets.QPushButton("Connect to datasource devices")
        self.conbtn.clicked.connect(self.con_clicked)
        self.startbtn = QtWidgets.QPushButton("Start logging")
        self.startbtn.clicked.connect(self.start_clicked)
        self.startbtn.setCheckable(True)

        layout.addRow(self.label)        
        layout.addRow(self.conbtn)
        layout.addRow(self.startbtn)

    def con_clicked(self):
        button = self.sender()
        self.connect.emit(self.device)        
            
    def start_clicked(self):
        button = self.sender()
        if button.isChecked():
            print("button pressed")
            self.device_start.emit(self.device)
            button.setText("Stop logging")
            self.conbtn.setEnabled(False)
        else:
            print('button released')
            self.device_stop.emit(self.device)
            button.setText("Start logging")
            self.conbtn.setEnabled(True)
            
            
    def thread_status(self,status):
        """ This function is called by redvypr whenever the thread is started/stopped
        """   
        self.update_buttons(status['threadalive'])

       
    def update_buttons(self,thread_status):
            """ Updating all buttons depending on the thread status (if its alive, graying out things)
            """
            if(thread_status):
                self.startbtn.setText('Stop reading data')
                self.startbtn.setChecked(True)
                #self.conbtn.setEnabled(False)
            else:
                self.startbtn.setText('Start reading data')
                #self.conbtn.setEnabled(True)




class displayDeviceWidget(QtWidgets.QWidget):
    """ Widget is showing heatflowsensor data
    """
    def __init__(self,dt_update = 0.5,device=None,buffersize=1000,tabwidget=None):
        funcname = __name__ + '.init()'
        super(QtWidgets.QWidget, self).__init__()
        self.layout_plot        = QtWidgets.QGridLayout(self)
        self.device = device
        self.tabname = 'Converted data plots'        
        self.dt_update = dt_update
        self.buffersizestd = buffersize
        self.plots = []
        
        # Add a widget with the data 
        if(tabwidget is not None):
            self.create_datadisplaywidget()
            #self.datadisplaywidget = QtWidgets.QWidget()            
            tabwidget.addTab(self.datadisplaywidget,'Sensor data')
            
        self.rawplot = QtWidgets.QWidget(self)
        self.layout_rawplot = QtWidgets.QGridLayout(self.rawplot)
        tabwidget.addTab(self.rawplot,'Rawdata data plots')                    
        self.create_dataplotwidget() # This widget is for plots of the data



                
    def create_dataplotwidget(self):
        funcname = __name__ + '.create_dataplotwidget()'
        # Add axes to the widget
        for i in range(6):
            if i == 0:
                logger.debug(funcname + ': Adding voltage plot')
                # The axes
                title = 'Heat flow voltage'
                location = [0,0]
                whichwidget = 0
                datetick = True
                ylabel = 'V'
                # The line to plot
                buffersize = self.buffersizestd
                xdata = np.zeros(buffersize) * np.NaN
                ydata = np.zeros(buffersize) * np.NaN
                name = 'HFS'
                lineplot = pyqtgraph.PlotDataItem( name = name )
                linewidth = 1
                color = QtGui.QColor(255,10,10)
                x = 't'
                y = 'hfV'

            elif i == 1:
                logger.debug(funcname + ': Adding heat flow plot')
                # The axes
                title = 'Heat flow'
                location = [0,0]
                whichwidget = 1                
                datetick = True
                ylabel = 'W/m**2'
                # The line to plot
                buffersize = self.buffersizestd
                xdata = np.zeros(buffersize) * np.NaN
                ydata = np.zeros(buffersize) * np.NaN
                name = 'HFS'
                lineplot = pyqtgraph.PlotDataItem( name = name )
                linewidth = 1
                color = QtGui.QColor(255,10,10)
                x = 't'
                y = 'hf'
            elif i == 2:
                logger.debug(funcname + ': Adding heat flow plot')
                # The axes
                title = 'Temperature voltage'
                location = [1,0]
                whichwidget = 0                
                datetick = True
                ylabel = 'V'
                # The line to plot
                buffersize = self.buffersizestd
                xdata = np.zeros(buffersize) * np.NaN
                ydata = np.zeros(buffersize) * np.NaN
                name = 'Temp [V]'
                lineplot = pyqtgraph.PlotDataItem( name = name )
                linewidth = 1
                color = QtGui.QColor(255,10,10)
                x = 't'
                y = 'NTCV'
            elif i == 3:
                logger.debug(funcname + ': Adding heat flow plot')
                # The axes
                title = 'Temperature'
                location = [1,0]
                whichwidget = 1                
                datetick = True
                ylabel = 'degC'
                # The line to plot
                buffersize = self.buffersizestd
                xdata = np.zeros(buffersize) * np.NaN
                ydata = np.zeros(buffersize) * np.NaN
                name = 'Temp '
                lineplot = pyqtgraph.PlotDataItem( name = name )
                linewidth = 1
                color = QtGui.QColor(255,10,10)
                x = 't'
                y = 'NTC'
            elif i == 4:
                logger.debug(funcname + ': Adding input voltage plot')
                # The axes
                title = 'Input voltage not scaled'
                location = [2,0]
                whichwidget = 0                
                datetick = True
                ylabel = 'V'
                # The line to plot
                buffersize = self.buffersizestd
                xdata = np.zeros(buffersize) * np.NaN
                ydata = np.zeros(buffersize) * np.NaN
                name = 'VINV'
                lineplot = pyqtgraph.PlotDataItem( name = name )
                linewidth = 1
                color = QtGui.QColor(255,10,10)
                x = 't'
                y = 'VIN'
            elif i == 5:
                logger.debug(funcname + ': Adding input voltage plot')
                # The axes
                title = 'Input voltage'
                location = [2,0]
                whichwidget = 1                
                datetick = True
                ylabel = 'V'
                # The line to plot
                buffersize = self.buffersizestd
                xdata = np.zeros(buffersize) * np.NaN
                ydata = np.zeros(buffersize) * np.NaN
                name = 'VIN'
                lineplot = pyqtgraph.PlotDataItem( name = name )
                linewidth = 1
                color = QtGui.QColor(255,10,10)
                x = 't'
                y = 'VIN'


            plot = pyqtgraph.PlotWidget(title=title)
            if(whichwidget == 1):
                self.layout_plot.addWidget(plot,location[0],location[1])
            else:
                self.layout_rawplot.addWidget(plot,location[0],location[1])
            if(datetick):
                axis = pyqtgraph.DateAxisItem(orientation='bottom')
                plot.setAxisItems({"bottom": axis})

            plot.setLabel('left', ylabel )
            if False:
                plot.setLabel('bottom', xlabel )

            plot_dict = {'widget':plot,'lines':[]}
            # Add a lines with the actual data to the graph
            if True:
                # Heat flow sensor Voltage
                logger.debug(funcname + ':Adding a line to the plot')
                # Configuration of the line plot
                lineconfig = {'device':self.device,'x':x,'y':y,'linewidth':linewidth,'color':color}
                # Add the line and the configuration to the lines list
                line_dict = {'line':lineplot,'config':lineconfig,'x':xdata,'y':ydata}
                # The lines are sorted according to the devicenames, each device has a list of lines attached to it
                plot_dict['lines'].append(line_dict)
                plot.addItem(lineplot)
                # Add the line to all plots
                self.plots.append(plot_dict)
            
        config = {'dt_update':self.dt_update,'last_update':time.time()}
        self.config = config



    def create_datadisplaywidget(self):
        """ Widget that shows the heatflowsensor data
        """
        self.datadisplaywidget = QtWidgets.QWidget()
        self.datadisplaywidget_layout = QtWidgets.QGridLayout(self.datadisplaywidget)
        self.snlabel       = QtWidgets.QLabel('Serialnumber')
        self.timelabel     = QtWidgets.QLabel('Time')
        fsize         = self.snlabel.fontMetrics().size(0, self.snlabel.text())
        self.snlabel.setFont(QtGui.QFont('Arial', fsize.height()+10))
        self.snlabel.setAlignment(QtCore.Qt.AlignCenter)        
        self.timelabel.setFont(QtGui.QFont('Arial', fsize.height()+10))
        self.timelabel.setAlignment(QtCore.Qt.AlignCenter)                
        self._datadisplays = {}
        self._datadisplays['hfV']  = datadisplay(title='Heat flow [V]')
        self._datadisplays['hf']   = datadisplay(title='Heat flow [W/m**2]')
        self._datadisplays['NTCV'] = datadisplay(title='Temperature [V]')
        self._datadisplays['NTC']  = datadisplay(title='Temperature [°C]')
        self._datadisplays['VIN']  = datadisplay(title='Input Voltage [V]')
        self._datadisplays['ts']  = datadisplay(title='Counter [s]')                                

        self.datadisplaywidget_layout.addWidget(self.snlabel,0,0,1,2)
        self.datadisplaywidget_layout.addWidget(self.timelabel,1,0,1,2)        
        self.datadisplaywidget_layout.addWidget(self._datadisplays['hfV'],2,0)
        self.datadisplaywidget_layout.addWidget(self._datadisplays['hf'],2,1)
        self.datadisplaywidget_layout.addWidget(self._datadisplays['NTCV'],3,0)
        self.datadisplaywidget_layout.addWidget(self._datadisplays['NTC'],3,1)
        self.datadisplaywidget_layout.addWidget(self._datadisplays['ts'],4,0)                
        self.datadisplaywidget_layout.addWidget(self._datadisplays['VIN'],4,1)                        
        
    
    def thread_status(self,status):
        """ This function is regularly called by redvypr whenever the thread is started/stopped
        """
        pass        
        #self.update_buttons(status['threadalive'])
        
    def update_line_styles(self):
        for plot_dict in self.plot_dicts:
            for line_dict in plot_dict['lines']:
                config = line_dict['config'] 
        
    def update(self,data):
        """ 
        """
        funcname = __name__ + '.update()'
        tnow = time.time()
        try:
            #print(funcname + 'got data',data)
            devicename = data['device']
            # Only plot the data in intervals of dt_update length, this prevents high CPU loads for fast devices
            update = (tnow - self.config['last_update']) > self.config['dt_update']

            if(update):
                self.config['last_update'] = tnow

            # Serialnumber (should stay the same though)
            self.snlabel.setText(data['sn'])
            # Update the time
            timestr = datetime.datetime.fromtimestamp(data['t']).strftime('%d %b %Y %H:%M:%S')
            self.timelabel.setText(timestr)
            # Update data display
            for key in self._datadisplays.keys(): # The keys are the same in the data structure
                newdata = float(data[key])
                self._datadisplays[key].set_data(newdata)

            # Update plots
            if True:
                # Loop over all plot axes
                for plot_dict in self.plots:
                    if True:
                        pw        = plot_dict['widget'] # The plot widget
                        for ind,line_dict in enumerate(plot_dict['lines']): # Loop over all lines of the devices to plot
                            line      = line_dict['line'] # The line to plot
                            config    = line_dict['config'] # The line to plot
                            x         = line_dict['x'] # The line to plot
                            y         = line_dict['y'] # The line to plot   
                            x         = np.roll(x,-1)
                            y         = np.roll(y,-1)
                            newx = float(data[config['x']])
                            newy = float(data[config['y']])
                            x[-1]    = newx
                            y[-1]    = newy
                            line_dict['x']  = x
                            line_dict['y']  = y
                            line.setData(x=x,y=y,pen = pyqtgraph.mkPen(config['color'], width=config['linewidth']))
        except Exception as e:
            logger.debug(funcname + ':' + str(e))



    

