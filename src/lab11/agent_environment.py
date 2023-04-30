import sys
import pygame
import random
from sprite import Sprite
from pygame_combat import run_pygame_combat
from pygame_human_player import PyGameHumanPlayer
from landscape import get_landscape, get_combat_bg
from pygame_ai_player import PyGameAIPlayer
import numpy as np
from pathlib import Path
import math


sys.path.append(str((Path(__file__) / ".." / "..").resolve().absolute()))

from lab2.cities_n_routes import get_randomly_spread_cities, get_routes
from lab7.ga_cities import create_cities


pygame.font.init()
game_font = pygame.font.SysFont("Comic Sans MS", 15)


#New AI Component
import torch


from transformers import AutoModelForCausalLM, AutoTokenizer
model_name = "gpt2-medium"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)


def get_landscape_surface(size):
    landscape = get_landscape(size)
    print("Created a landscape of size", landscape.shape)
    pygame_surface = pygame.surfarray.make_surface(landscape[:, :, :3])
    return pygame_surface,landscape


def get_combat_surface(size):
    landscape = get_combat_bg(size)
    print("Created a landscape of size", landscape.shape)
    pygame_surface = pygame.surfarray.make_surface(landscape[:, :, :3])
    return pygame_surface


def setup_window(width, height, caption):
    pygame.init()
    window = pygame.display.set_mode((width, height))
    pygame.display.set_caption(caption)
    return window


def displayCityNames(city_locations, city_names):
    for i, name in enumerate(city_names):
        text_surface = game_font.render(str(i) + " " + name, True, (0, 0, 150))
        screen.blit(text_surface, city_locations[i])


def get_route_cost(routes, game_map, routenum):

    route_coordinate = routes[routenum]
    x1 = route_coordinate[0][0]
    y1 = route_coordinate[0][1]
    x2 = route_coordinate[1][0]
    y2 = route_coordinate[1][1]

    from bresenham import bresenham
    path = list(bresenham(x1,y1,x2,y2)) 
    damage = game_map[tuple(zip(*path))].sum() % 1000
    return damage


def ValidRoute(routes, current, new):
    start_city = cities[current]
    end_city = cities[new]
    for route in routes:
        if np.array_equal(route[:2], [start_city, end_city]) or \
           np.array_equal(route[:2], [end_city, start_city]):
            return True
    return False

def GetRoute(routes,current,new):
    start_city = cities[current]
    end_city = cities[new]
    i = 0
    for route in routes:
        if np.array_equal(route[:2], [start_city, end_city]) or \
           np.array_equal(route[:2], [end_city, start_city]):
            return i
        i += 1
    return 0

class State:
    def __init__(
        self,
        current_city,
        destination_city,
        travelling,
        encounter_event,
        cities,
        routes,
        bal,
    ):
        self.current_city = current_city
        self.destination_city = destination_city
        self.travelling = travelling
        self.encounter_event = encounter_event
        self.cities = cities
        self.routes = routes
        self.bal = 1000


if __name__ == "__main__":
    size = width, height = 640, 480
    black = 1, 1, 1
    start_city = 0
    end_city = 9
    sprite_path = "assets/lego.png"
    sprite_speed = 1

    screen = setup_window(width, height, "Game World Gen Practice")

    landscape_surface, landscape = get_landscape_surface(size)
    combat_surface = get_combat_surface(size)
    city_names = [
        "Morkomasto",
        "Morathrad",
        "Eregailin",
        "Corathrad",
        "Eregarta",
        "Numensari",
        "Rhunkadi",
        "Londathrad",
        "Baernlad",
        "Forthyr",
    ]

    # GA 
    cities = create_cities(size, len(city_names))
    #cities = get_randomly_spread_cities(size,len(city_names))
    routes = get_routes(cities)

    random.shuffle(routes)
    routes = routes[:10]

    player_sprite = Sprite(sprite_path, cities[start_city])

    player = PyGameHumanPlayer()

    #player = PyGameAIPlayer()

    """ Add a line below that will reset the player variable to 
    a new object of PyGameAIPlayer class."""

    state = State(
        current_city=start_city,
        destination_city=start_city,
        travelling=False,
        encounter_event=False,
        cities=cities,
        routes=routes,
        bal = 1000,
    )

    while True:
        action = player.selectAction(state)
        if 0 <= int(chr(action)) <= 9:
            if int(chr(action)) != state.current_city and not state.travelling and ValidRoute(routes,state.current_city,int(chr(action))):
                #Gets the route number
                route = GetRoute(routes,state.current_city,int(chr(action)))
                state.bal -= get_route_cost(routes,landscape,route)
                print(f"Your current balance is ",state.bal)
                if(state.bal <= 0):
                    print("You are penniless You Lose!")
                    break
                start = cities[state.current_city]
                state.destination_city = int(chr(action))
                destination = cities[state.destination_city]
                player_sprite.set_location(cities[state.current_city])
                state.travelling = True
                print(
                    "Travelling from", state.current_city, "to", state.destination_city
                )
                #Give some money For arriving as a way for "selling goods"
                state.bal += random.randint(100,700)
                print("After Selling Goods Your Balance is ", state.bal)

        screen.fill(black)
        screen.blit(landscape_surface, (0, 0))

        for city in cities:
            pygame.draw.circle(screen, (255, 0, 0), city, 5)

        for line in routes:
            pygame.draw.line(screen, (255, 0, 0), *line)

        displayCityNames(cities, city_names)
        if state.travelling:
            state.travelling = player_sprite.move_sprite(destination, sprite_speed)
            state.encounter_event = random.randint(0, 1000) < 2
            if not state.travelling:
                print('Arrived at', state.destination_city)

        if not state.travelling:
            encounter_event = False
            state.current_city = state.destination_city

        if state.encounter_event:
            val = run_pygame_combat(combat_surface, screen, player_sprite)
            state.encounter_event = False
            if val == -1 or val == 0: #Checks the return of the combat if it is a draw or a loss end the game
                print('You have drawn your last breath game over!')
                prompt = "As I draw my last breath I sit here and contemplate"
                input_ids = tokenizer.encode(prompt, add_special_tokens=True, return_tensors='pt')

                # Generate text using the model
                output = model.generate(
                    input_ids,
                    max_length=100,
                    pad_token_id=tokenizer.eos_token_id,
                    do_sample=True,
                    temperature=1.0,)

                # Decode the generated text and print it
                generated_text = tokenizer.decode(output[0], skip_special_tokens=True)
                print(generated_text)
                break
            else:
                #If win battle give random money as loot
                state.bal += random.randint(100,700)
                print("After Looting Your Balance is ", state.bal)
        else:
            player_sprite.draw_sprite(screen)
        pygame.display.update()
        if state.current_city == end_city:
            print('You have reached the end of the game!')
            break
