"""
After we saw how to control each player using event logic,
could we use similar logic to do the same for a multiplayer game?
Instead of directly controlling each player, we could let commands 
comming from a specific player be passed to a "dot" instance to move
it. 

First however, lets get a comms example that will let players wanting
to be added to the same game get added and basically "appear" when they
send a message to the same game queue you are on. 
"""
import pygame
from random import randint
import json
import sys
from rich import print
from threading import Thread
import math
import os
from pygame.math import Vector2

import pygame.display


# necessary libs for rabbitmq
from comms import CommsListener
from comms import CommsSender


with open("colors.json") as f:
    colors = json.load(f)


class MyVector22(object):
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.tuple = (self.x, self.y)

    def __str__(self):
        return f"({self.x}, {self.y})"

    @property
    def magnitude(self):
        return math.sqrt(self.x**2 + self.y**2)

    def normalize(self):
        self.x /= self.magnitude
        self.y /= self.magnitude

    @staticmethod
    def create_path(destination, pos):
        return MyVector22(destination.x - pos.x, destination.y - pos.y)

    @staticmethod
    def dot(v1, v2):
        return v1.x * v2.x + v1.y * v2.y


class Messenger:
    def __init__(self, creds, callback=None):
        self.creds = creds
        self.callBack = callback

        if not self.creds:
            print(
                "Error: Message handler needs `creds` or credentials to log into rabbitmq. "
            )
            sys.exit()

        if not self.callBack:
            print(
                "Error: Message handler needs a `callBack` function to handle responses from rabbitmq. "
            )
            sys.exit()

        # Identify the user
        self.user = self.creds["user"]

        # create instances of a comms listener and sender
        # to handle message passing.
        self.commsListener = CommsListener(**self.creds)
        self.commsSender = CommsSender(**self.creds)

        # Start the comms listener to listen for incoming messages
        self.commsListener.threadedListen(self.callBack)

    def send(self, **kwargs):
        """Sends the message to a target or broadcasts to all."""
        target = kwargs.get("target", "broadcast")
        self.commsSender.threadedSend(
            target=target, sender=self.user, body=json.dumps(kwargs), debug=False
        )


# class Icon(pygame.sprite.Sprite):
#     def __init__(self, start, end):
#         super().__init__()
#         # setup
#         self.image = pygame.Surface((40, 40))
#         self.image.fill("red")
#         self.pos = Vector2(start)
#         self.rect = self.image.get_rect(center=start)

#         # positions
#         self.direction = Vector2(end) - Vector2(start)
#         self.speed = 10  # changing this changes the direction the sprite moves
#         self.moving = False

#     def move(self):
#         self.moving = True

#     def update(self):
#         if self.moving:
#             self.pos += self.direction.normalize() * self.speed
#             self.rect.center = (round(self.pos.x), round(self.pos.y))


class BasicPlayer(pygame.sprite.Sprite):
    def __init__(self, **kwargs):
        """_summary_

        Args:
            color (tuple)           : rgb value (r,g,b)
            id (string)             : unique identifier for player
            location (tuple)        : (x,y)
            screen (pygame surface) : pygame surface to display player
        """
        # init sprite base class
        super(BasicPlayer, self).__init__()

        # get player basics from kwargs
        self.screen = kwargs.get("screen", None)  # copy of screen to display dot on
        self.name = kwargs.get("name", None)
        self.color = kwargs.get(
            "color", (randint(0, 256), randint(0, 256), randint(0, 256))
        )
        # get starting player location from kwargs
        self.location = kwargs.get("location", (randint(25, 400), randint(25, 400)))
        # convert tuple to a vector
        self.location = pygame.math.Vector2(self.location)

        # sprite stuff
        self.surf = pygame.Surface((10, 10))
        self.surf.fill(self.color)
        self.rect = self.surf.get_rect(
            center=(
                self.location.x,
                self.location.y,
            )
        )

        self.speed = 1
        self.ticks = 0
        self.width, self.height = self.screen.get_size()
        self.lastUpdated = pygame.time.get_ticks()
        self.velocity = pygame.math.Vector2()
        self.direction = (1, 1)
        self.target = (0, 0)

    def move(self, keys=None):
        """Change player position based on velocity or stop if
        space bar is pressed.
        https://stackoverflow.com/questions/68486375/moving-with-a-normalized-vector-in-pygame-inconsistent
        """
        # print(f"updating {self.color}")
        if keys:
            if keys[pygame.K_SPACE]:
                self.velocity.x = 0
                self.velocity.y = 0

        # Move the sprite towards the target each frame
        self.location.x += self.velocity.x
        self.location.y += self.velocity.y

        self.rect.move_ip(self.velocity.x, self.velocity.y)
        self.rect.left += self.velocity.x
        self.rect.top += self.velocity.y

        if self.location.x > self.width:
            self.location.x = 0
        if self.location.x < 0:
            self.location.x = self.width
        if self.location.y > self.height:
            self.location.y = 0
        if self.location.y < 0:
            self.location.y = self.height

        # # Keep player on the screen
        if self.rect.left <= 0:
            self.rect.right = self.width
        if self.rect.right > self.width:
            self.rect.left = 0
        if self.rect.top <= 0:
            self.rect.bottom = self.height
        if self.rect.bottom >= self.height:
            self.rect.top = 0

    def goto(self, target_x, target_y):
        """Starts player moving towards the x,y coords passed
        in from a mouse click event.
        """
        distance = math.sqrt(
            (target_x - self.location.x) ** 2 + (target_y - self.location.y) ** 2
        )
        self.direction = (
            target_x - self.location.x,
            target_y - self.location.y,
        )

        # Normalize the direction vector to get a unit vector
        direction_normalized = pygame.math.Vector2(self.direction).normalize()

        # Calculate the velocity vector by multiplying the direction vector by the speed
        self.velocity = direction_normalized * self.speed

    def setSpeed(self, speed):
        self.speed = speed
        direction_normalized = pygame.math.Vector2(self.direction).normalize()

        # change velocity based on input speed
        self.velocity = direction_normalized * self.speed

    def update(self, keys=None):
        """Updates position and calls draw for player"""
        self.move(keys)
        self.draw()

    def draw(self):
        """Draws the dot. Could be more complex for an animated sprite or
        similar, but one line is good for now.
        """
        # draw the dot
        pygame.draw.circle(self.screen, self.color, self.location, 10)


class Player(BasicPlayer):
    def __init__(self, **kwargs):
        """Extends BasicPlayer to add messaging capabilities to a player.

        Args:
            callback (function)     : callback function to handle messages.
            color (tuple)           : tuple of (r,g,b)
            creds (json)            : credentials for messaging back end
            name (string)           : unique identifier
            screen (pygame surface) : pygame surface to display player
        """

        super().__init__(**kwargs)

        self.creds = kwargs.get("creds", None)
        self.callback = kwargs.get("callback", None)
        self.id = self.creds["user"]
        self.messenger = Messenger(self.creds, self.callback)
        self.lastBroadcast = pygame.time.get_ticks()
        self.broadCastDelay = 50

    def timeToBroadCast(self):
        """check to see if there was enough delay to broadcast again"""
        return pygame.time.get_ticks() - self.lastBroadcast > self.broadCastDelay

    def broadcastData(self, data):
        """Sends data to all other players in the game.

        Args:
            data (dict) : key value dict of data to send
        """
        if self.timeToBroadCast():
            self.messenger.send(
                target="broadcast", sender=self.id, player=self.id, data=data
            )
            self.lastBroadcast = pygame.time.get_ticks()
            return True

        return False

    def goto(self, target_x, target_y):
        """Overloaded method which simply calls parent "goto" method, but
            necessary since this method needs to broadcast a target xy to
            other players and base class doesn't have messaging capabilities.
        Args:
            x (int) : x coord
            y (int) : y coord
        """
        # print("child goto")
        self.target = (target_x, target_y)
        super(Player, self).goto(target_x, target_y)
        print("broadcasting target")
        self.broadcastData(
            {
                "target": self.target,
                "location": (self.location.x, self.location.y),
                "speed": self.speed,
                "color": self.color,
            }
        )

    def setSpeed(self, speed):
        """Yup. This sets the players speed.
            It also broadcasts the speed to everyone else.
        Args:
            speed (int) : players speed
        """
        super(Player, self).setSpeed(speed)
        print("broadcasting speed")
        self.broadcastData(
            {
                "target": self.target,
                "location": (self.location.x, self.location.y),
                "speed": self.speed,
                "color": self.color,
            }
        )


class GameManager:
    def __init__(self, screen):
        self.players = {}
        self.screen = screen
        self.localPlayer = None
        self.sprites = pygame.sprite.Group()

    def addPlayer(self, **kwargs):
        name = kwargs.get("name", None)
        player = kwargs.get("player", None)
        color = kwargs.get("color", None)
        localPlayer = kwargs.get("localPlayer", False)

        # we don't want to try and manage the local player instance
        if localPlayer:
            self.localPlayer = player
            return

        # this is a new player that needs just a basic player class
        # with no messaging capabilites. This is a mirror of another
        # player somewhere else.
        player = BasicPlayer(screen=self.screen, name=name, color=color)
        self.players[name] = player

        self.sprites.add(player)

    def update(self):
        """Update all players registered with the game manager."""
        for id, player in self.players.items():
            player.update()

        for entity in self.sprites:
            self.screen.blit(entity.surf, entity.rect)

        if pygame.sprite.spritecollideany(self.localPlayer, self.sprites):
            print("collision!!")

    def callBack(self, ch, method, properties, body):
        """_summary_: callback for multiple players

        Args:
            ch (pika): type of channel connection with rabbitmq
            method (pika): async info
            properties (pika): general info about connection
            body (dict): only thing that really matters. This is your data

        Returns:
            dictionary: results of callback
        """

        game = method.exchange
        exchange = method.exchange
        body = json.loads(body.decode("utf-8"))
        data = body.get("data", None)
        sender = body["sender"]
        xy = data.get("location", None)
        target = data.get("target", None)
        color = data.get("color", None)
        speed = data.get("speed", None)

        if self.localPlayer != sender:
            if not sender in self.players:
                self.addPlayer(name=sender, color=color)
                print(f"Players: {len(self.players)}")
            else:
                if xy:
                    self.players[sender].location.x = xy[0]
                    self.players[sender].location.y = xy[1]
                    self.players[sender].rect.center = xy
                if target:
                    print(f"{sender} goto to {target}")
                    self.players[sender].goto(target[0], target[1])
                if speed:
                    print(f"{sender} speed to {speed}")
                    self.players[sender].setSpeed(speed)
                if color:
                    print(f"{sender} color to {color}")
                    self.players[sender].color = color


############################################################
# GLOBALS
############################################################
class Globals:
    """A class mainly for one reason,"""

    winx = 0
    winy = 0
    winsize = (400, 400)
    screen = None
    clock = None
    fps = 60

    def __new__(cls, x, y):
        os.environ["SDL_VIDEO_WINDOW_POS"] = "%d,%d" % (int(x), int(y))
        pygame.init()
        cls.screen = pygame.display.set_mode(cls.winsize)
        cls.clock = pygame.time.Clock()
        instance = super().__new__(cls)
        return instance


def main(creds, x, y, color=None):
    globals = Globals(x, y)
    manager = GameManager(globals.screen)

    localPlayer = Player(
        screen=globals.screen, creds=creds, callback=manager.callBack, color=color
    )

    manager.addPlayer(player=localPlayer, localPlayer=True)

    # set the window title
    pygame.display.set_caption(f"{creds['user']}")

    # create list for lookup for keys 0-9
    # The keys 0-9 are ascii 48-57
    numericKeys = [x for x in range(48, 58)]

    # run the game loop
    running = True
    while running:
        # clear the screen
        globals.screen.fill((255, 255, 255))

        # handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_SPACE:
                    localPlayer.update(keys)
                # get the keys 0-9 if pressed
                elif event.key in numericKeys:
                    print(f"Speed set to: {event.key-48}")
                    # choose current dot by which key pressed
                    localPlayer.setSpeed(event.key - 48)

            elif event.type == pygame.MOUSEBUTTONUP:
                # Get the position of the mouse click
                mouse_x, mouse_y = pygame.mouse.get_pos()
                localPlayer.goto(mouse_x, mouse_y)

        # move the dot based on key input
        keys = pygame.key.get_pressed()
        localPlayer.update(keys)

        manager.update()

        # update the screen
        pygame.display.flip()

        globals.clock.tick(globals.fps)

    # quit Pygame
    pygame.quit()


def mykwargs(argv):
    """
    Processes argv list into plain args and kwargs.
    Just easier than using a library like argparse for small things.
    Example:
        python file.py arg1 arg2 arg3=val1 arg4=val2 -arg5 -arg6 --arg7
        Would create:
            args[arg1, arg2, -arg5, -arg6, --arg7]
            kargs{arg3 : val1, arg4 : val2}

        Params with dashes (flags) can now be processed seperately
    Shortfalls:
        spaces between k=v would result in bad params
    Returns:
        tuple  (args,kargs)
    """
    args = []
    kargs = {}

    for arg in argv:
        if "=" in arg:
            key, val = arg.split("=")
            kargs[key] = val
        else:
            args.append(arg)
    return args, kargs


if __name__ == "__main__":
    """ """
    args, kwargs = mykwargs(sys.argv)

    queue = kwargs.get("queue", None)
    player = kwargs.get("player", None)
    windowLocation = kwargs.get("windowLocation", (100, 100))
    color = kwargs.get("color", "Red")

    color = colors[color]["rgb"]

    print(windowLocation)

    if not isinstance(windowLocation, tuple):
        windowLocation = tuple(windowLocation.split(","))

    x, y = windowLocation

    if None in [queue, player]:
        print("Need: queue and player ")
        print(
            "Example: python ex_99.py queue=game-01 player=player-01 windowLocation=100,100 color=blue"
        )
        sys.exit()

    creds = {
        "exchange": queue,
        "port": "5672",
        "host": "terrywgriffin.com",
        "user": player,
        "password": player + "2023!!!!!",
    }

    main(creds, x, y, color)