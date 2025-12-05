from turtle import *
from time import sleep
import random
import colorsys

BG_COLOR = "#FF3C3C"
PEN_SHAPE = "circle"
SHAPE_SIZE = 0.5 # scalar to change size of pen shape.
PATH_SCALAR = .5 # scales the size of the path
BOUNDARY_SCALE = 1 # how much of the window should the path be confined to. 1 is the full window. 0.5 would be half the window.
SPEED_MODE = "fastest" # "slow", "normal", "fast", "faster", "fastest", or "instant"
FILL_MODE = "half" # "line", "half", "thick", or "full"
MANUAL = False
STEPS = None

ENABLE_COLOR = False # enable dynamic color generation while building maze.
# START_COLOR = (.2, .4, 1.0) # set start color RGB values
COLOR_SPEED = 1 # in degrees, meaning 360 would be a full rotation, 180 for complementary, 120/270 for triads
COLOR_ACCELERATION = 0.01 # how much should the color speed accelerate by, in degrees.
MAX_COLOR_SPEED = 20 # limits acceleration/speed to a certain speed. If speed exceeds 360, it will effectively wrap around to a speed of `color_speed % 360`

class ColorManager:
    def __init__(self, start_color, color_speed, acceleration=0, max_color_speed=120):
        self.color = start_color
        self.speed = color_speed
        self.acceleration = acceleration
        self.max_speed = max_color_speed
        self.hit_max = False
        self.color_shift = 0
        self.max_speed_counter = 0
        pencolor(self.color)

    def __str__(self):
        return f"[COLOR] The current color is {self.color_string()}. The color has been shifted by {self.color_shift:.2f} degrees across all branches."
    
    def color_string(self):
        return f"(R:{self.color[0]:.2f}, G:{self.color[1]:.2f}, B:{self.color[2]:.2f})"

    def shift_hue(self, shift_deg, back_tracking=False):
        r, g, b = self.color
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        h = (h + shift_deg / 360.0) % 1.0
        s = max(s, 0.5)
        v = max(v, 0.8)
        self.set_color(colorsys.hsv_to_rgb(h, s, v))

        if not back_tracking:
            self.color_shift += abs(shift_deg)

    def set_color(self, new_color=None):
        if new_color != None:
            self.color = new_color
            pencolor(new_color)
        else:
            pencolor(self.color)

    def get_color(self):
        return self.color
    
    def accelerate(self, forward=True):
        if forward:
            if self.speed < self.max_speed:
                self.speed = self.speed + self.acceleration
            elif not self.hit_max:
                print(f"[COLOR]: Max speed of {self.max_speed} has been reached. Speed will drop while retracing.")
                self.hit_max = True
                # necessary to keep track of how long speed has been held at max, when retracing, do not dellerate on spaces where no acceleration was added.
                self.max_speed_counter += 1 
            else:
                self.max_speed_counter += 1 
        else:
            if self.max_speed_counter > 0:
                self.max_speed_counter -= 1
            else:
                self.speed = self.speed - self.acceleration

    def step_color(self, direction):
        self.accelerate() # consider only accelerating on turns
        if direction == "left":
            self.shift_hue(self.speed)
        if direction == "right":
            self.shift_hue(-self.speed)
    
    def undo_color_step(self, direction):
        if direction == "left":
            self.shift_hue(-self.speed, True)
        if direction == "right":
            self.shift_hue(self.speed, True)
        self.accelerate(forward=False)
    

class WalkGenerator:
    def __init__(
            self, 
            bg_color="white",
            pen_shape="arrow",
            shape_size=1,
            path_scalar=1,
            boundary_scale=1,
            enable_color=False,
            color_manager:ColorManager|None =None,
            speed_mode="normal", # speedmodes are "slow", "normal", "fast", and "faster"     
            fill=False,
            steps=None
            ):
        self.t : Turtle = getturtle()
        self.screen = self.t.screen
        speed(0)
        if speed_mode != "slow":
            self.set_speedmode(speed_mode)
        self.simple_choices = ["forward", "left", "right"]
        colormode(1)
        self.screen_size = screensize()
        self.boundary_scale = boundary_scale
        self.x_extreme = int(self.screen_size[0]*BOUNDARY_SCALE)
        self.y_extreme = int(self.screen_size[1]*BOUNDARY_SCALE)
        self.shape = pen_shape
        shape(self.shape)
        resizemode("user")
        self.shape_size = shape_size # default to smaller shape size
        shapesize(self.shape_size, self.shape_size)
        self.bg = bg_color
        bgcolor(self.bg)
        self.path_size = 10 * path_scalar
        self.color_on = enable_color
        self.set_fillmode(fill)
        if self.color_on:
            if color_manager:
                self.cm = color_manager
            else:
                raise ValueError("[ERROR] If 'enable_color' is set to True, a ColorManager must be provided.")
        self.steps = steps
        # dynamic values
        self.position = pos()
        self.direction = heading()
        self.history = []
        self.steps_taken = 0
        self.steps_back = 0
        self.visited = set()
        self.complete = False
        self.backtracking = False

    def reset(self):
        reset()
        showturtle()
        colormode(1)
        resizemode("user")
        bgcolor(self.bg)
        shape(self.shape)
        shapesize(self.shape_size, self.shape_size)
        self.history=[]
        self.position=pos()
        self.direction=heading()
        self.steps_taken = 0
        self.steps_back = 0
        self.visited = set()
        self.complete = False

    def set_bg_color(self, color):
        self.bg = color
        bgcolor(self.bg)

    def set_shape(self, pen_shape):
        self.shape = pen_shape
        shape(self.shape)

    def set_shape_size(self, size):
        self.shape_size = size * 0.4 # default to smaller shape size
        shapesize(self.shape_size, self.shape_size)

    def set_fillmode(self, fillmode):
        self.fillmode = fillmode
        if self.fillmode == "line":
            pensize(1)
        if self.fillmode == "half":
            pensize(int(self.path_size/2))
        if self.fillmode == "thick":
            pensize(int(self.path_size*0.8))
        if self.fillmode == "full":
            pensize(int(self.path_size))

    def set_speedmode(self, speed_mode):
        self.speedmode = speed_mode
        if self.speedmode == "slow":
            self.screen.tracer(1, 5)
            speed(0)
        elif self.speedmode == "normal":
            self.screen.tracer(1, 1)
        elif self.speedmode == "fast":
            self.screen.tracer(5, 0)
        elif self.speedmode == "faster":
            self.screen.tracer(250, 0)
        elif self.speedmode == "fastest":
            self.screen.tracer(500, 0)
        elif self.speedmode == "instant":
            self.screen.tracer(0, 0)

    def random_walk_simple(self, steps):  
        for i in range(steps):
            direction = random.choice(self.simple_choices)
            if self.color_on:
                self.cm.step_color(direction)
            match direction:
                case "forward":
                    forward(self.path_size)
                case "left":
                    left(90)
                    forward(self.path_size)
                case "right":
                    right(90)
                    forward(self.path_size)

    def undo_step(self):
        if len(self.history) < 1:
            return True
        last_move = self.history.pop()
        back(self.path_size)
        if self.color_on:
            self.cm.undo_color_step(last_move)
        if last_move == "right":
            left(90)
        if last_move == "left":
            right(90)
        return False
    
    def check_next_position(self):
        self.position = pos()
        self.direction = heading()
        match self.direction:
            case 0.0:
                next_position = (self.position[0]+self.path_size, self.position[1])
            case 90.0:
                next_position = (self.position[0], self.position[1]+self.path_size)
            case 180:
                next_position = (self.position[0]-self.path_size, self.position[1])
            case _:
                next_position = (self.position[0], self.position[1]-self.path_size)
        return (round(next_position[0]), round(next_position[1]))
    
    def check_boundaries(self, next_position):
        if abs(next_position[0]) > self.x_extreme:
            return False
        elif abs(next_position[1]) > self.y_extreme:
            return False
        else:
            return True

    def check_directions(self):
        available_choices = []
        forward_position = self.check_next_position()
        if (forward_position not in self.visited) and self.check_boundaries(forward_position):
            available_choices.append("forward")
        right(90)
        right_position = self.check_next_position()
        if (right_position not in self.visited) and self.check_boundaries(right_position):
            available_choices.append("right")
        left(180)
        left_position = self.check_next_position()
        if (left_position not in self.visited) and self.check_boundaries(left_position): 
            available_choices.append("left")
        right(90)
        if self.backtracking and len(available_choices) > 0:
            print(f"[WALK] Retrace complete... {self.steps_back} steps backward so far. {len(self.history)} moves in history.")
            pendown()
            self.backtracking = False
        return available_choices

    def manual_step(self, x, y):
        self.step()
        update()

    def step(self):
        self.position = pos()
        rounded_position = (round(self.position[0]), round(self.position[1]))
        self.visited.add(rounded_position)
        available = self.check_directions()
        if len(available) == 0:
            if not self.backtracking:
                print(f"[WALK] NO CHOICES AVAILABLE. TURTLE CORNERED IN {self.steps_taken} STEPS. \n[WALK] Retracing... {len(self.history)} moves in history.")
                self.backtracking = True
                penup()
            history_empty = self.undo_step()
            if history_empty:
                print("[WALK] MOVE HISTORY EMPTY. PATH COMPLETE")
                print(f"[WALK] Final size of the 'visited' set was {len(self.visited)}")
                self.t.hideturtle()
                if self.color_on:
                    print(self.cm)
                self.screen.update()
                self.complete = True
            self.steps_back += 1
            return False
        direction = random.choice(available)
        self.history.append(direction)
        if direction == "left":
            left(90)
            forward(self.path_size)
        if direction == "right":
            right(90)
            forward(self.path_size)
        if direction == "forward":
            forward(self.path_size)
        if self.color_on:
            self.cm.step_color(direction)

        self.steps_taken += 1
        if self.steps != None:
            if self.steps <= self.steps_taken:
                self.complete = True
        return True

    def random_walk(self, manual=False):
        if not manual:
            while not self.complete:
                self.step()
        else:
            self.screen.onclick(self.manual_step)


start_hue = random.randrange(0, 360)
start_color = colorsys.hsv_to_rgb((start_hue/360)%1.0, 0.8, 0.8)
if ENABLE_COLOR:
    cm = ColorManager(start_color, COLOR_SPEED, COLOR_ACCELERATION, MAX_COLOR_SPEED)
else:
    cm = None
wg = WalkGenerator(BG_COLOR, PEN_SHAPE, SHAPE_SIZE, PATH_SCALAR, BOUNDARY_SCALE, ENABLE_COLOR, cm, SPEED_MODE, FILL_MODE, STEPS)
wg.random_walk(MANUAL)

wg.screen.mainloop()