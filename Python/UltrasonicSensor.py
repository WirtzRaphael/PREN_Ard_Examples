#!/usr/bin/python

import threading
import time
import logging
import RPi.GPIO as GPIO


logging.basicConfig(level=logging.CRITICAL)

log = logging.getLogger(__name__)
GPIO.setmode(GPIO.BOARD)


class UltrasonicSensor:
    def __init__(self, trigger_pin, echo_pin, n=3):
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        self.n = n
        self.counter = 0

        self.values = [0] * n
        self.no_echo = False
        self.enabled = True

        log.debug("Setup Trigger %d, Echo %d" % (trigger_pin, echo_pin))
        GPIO.setup(echo_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(trigger_pin, GPIO.OUT)

        self.write_pin(0)

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enable = False

    def read_pin(self):
        return GPIO.input(self.echo_pin)

    def write_pin(self, state):
        GPIO.output(self.trigger_pin, state)

    def trigger(self):
        self.write_pin(1)
        time.sleep(.00001)
        self.write_pin(0)

    def convert_to_cm(self, delay_time):
        return (delay_time * 1E6) / 58

    def mean(self):
        return float(sum(self.values)) / max(len(self.values), 1)

    def get_last_value(self):
        return self.values[self.n - 1]

    def __get_value__(self):
        log.debug("Trigger on pin: %d" % self.trigger_pin)
        self.trigger()

        start = time.time()
        c2 = GPIO.wait_for_edge(self.echo_pin, GPIO.RISING, timeout=60)
        pulse = time.time()
        c2 = GPIO.wait_for_edge(self.echo_pin, GPIO.FALLING, timeout=30)

        pulse_duration = time.time() - pulse

        if c2 is None:
            log.debug("No Echo on pin: %d " % self.echo_pin)
            self.no_echo = True

        else:
            self.no_echo = True
            distance = self.convert_to_cm(pulse_duration)
            log.info("echo " + str(distance) + "cm from pin:" + str(self.trigger_pin))
            measurement_time = time.time() - start

            self.counter += 1

            self.values[self.counter % self.n] = distance

            if measurement_time < .06:
                log.debug("delay for next measurement")
                time.sleep(.06 - measurement_time)
            return distance


class SensorArray:

    LF = 0
    LR = 1
    RF = 2
    RR = 3
    FL = 4
    FR = 5

    trigger_pins =  [3, 5, 7, 11, 13, 19] # 15
    echo_pins =     [16, 18, 22, 24, 26, 40]# 28 doesn't work for some reason

    def __init__(self):
        self.sensors = [None] * len(self.trigger_pins)
        self.n_sensors = range(len(self.trigger_pins))
        self.running = True
        self.init = 0  # Keeps count when initalising Sensors

        for sensor_nr in self.n_sensors:
            self.__add_sensor__(sensor_nr)

    def __add_sensor__(self, nr):
        self.sensors[nr] = UltrasonicSensor(self.trigger_pins[nr], self.echo_pins[nr])

    def start_measurement_loop(self):
        self.running = True
        while self.running:
            for sensor in self.sensors:
                if sensor.enabled:
                    sensor.__get_value__()

    def disable_all(self):
        for sensor in self.sensors:
               sensor.disable()

    def enable_all(self):
        for sensor in self.sensors:
               sensor.enable()

    def enable_right(self):
        self.disable_all()
        self.sensors[self.RF].enable()
        self.sensors[self.RR].enable()

    def enable_left(self):
        self.disable_all()
        self.sensors[self.LF].enable()
        self.sensors[self.LR].enable()

    def stop_measurement_loop(self):
        self.running = False


if __name__ == "__main__":
    # logs sensor data on disk

    a = SensorArray()

    #t1 = threading.Thread(target=a.start_partial_loop, args=([SensorArray.LF, SensorArray.LR],))
    t1 = threading.Thread(target=a.start_measurement_loop)
    t1.start()
    time.sleep(1)

    while True:
        with open("sensor.log", "a") as f:
            for i, sensor in enumerate(a.sensors):
                f.write("{:.2f};".format(sensor.mean()))

                print i, "%.2f" % sensor.mean(),
            print "*"

            f.write("\n")
            time.sleep(.06 * len(a.sensors))
            #time.sleep(.12) #########################################################################DEBUG

    a.stop_measurement_loop()
    t1.join()
    log.info("stoped gracefully")
