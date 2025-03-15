import pygame
import random
import math
import json
import os
import shutil
from pygame.locals import *
import tkinter as tk
from tkinter import filedialog


pygame.init()
pygame.mixer.init()
clock = pygame.time.Clock()

w = 1920
h = 1080

screen = pygame.display.set_mode((w, h), FULLSCREEN | SCALED)
pygame.display.set_caption("Oku!Rwa")


celownik = pygame.image.load("celownik.png").convert_alpha()
tlo = pygame.image.load("tlo.jpg").convert_alpha()
mods_img = pygame.image.load("mods.png").convert_alpha()  


hit_sound = pygame.mixer.Sound("hit.mp3")


trail_size = 15
trail_color = (0, 255, 255)
trail_positions = []


rect = celownik.get_rect()


SCREEN_WIDTH = w
SCREEN_HEIGHT = h
CIRCLE_RADIUS = 45          
APPROACH_RADIUS = 105      
CIRCLE_COLOR = (255, 0, 0)     
APPROACH_COLOR = (255, 0, 0)   
BACKGROUND_COLOR = (0, 0, 0)
CIRCLE_SPAWN_TIME = 2000  


font = pygame.font.Font(None, 40)
title_font = pygame.font.Font(None, 90)
small_font = pygame.font.Font(None, int(40 * 0.7))  


speed_multiplier = 2.0
spawn_multiplier = 3.0


circle_size_multiplier = 1.0  

saved_slider1_value = 6      
saved_slider2_value = 11     
saved_circle_size_multiplier = 10  


saved_slider3_value = 100


circle_spawn_counter = 0


hit_count = 0
attempts = 0
accuracy_sum = 0


hit_errors = []


spawn_area_width = int(w * 0.75)
spawn_area_height = int(h * 0.75)
spawn_area_x = (w - spawn_area_width) // 2
spawn_area_y = (h - spawn_area_height) // 2 + 20


overlay = pygame.Surface((w, h))
overlay.fill((0, 0, 0))


click_key1 = pygame.K_z 
click_key2 = pygame.K_x  
selected_keybind = None


keybind1_count = 0
keybind2_count = 0
mouse_left_count = 0
mouse_right_count = 0


disable_mouse = False


square_highlights = {}


imported_map_filename = None


combo = 0
combo_animation_start = 0


def draw_hp_bar(surface, hp):
    hp_x = 10
    hp_y = 10
    hp_size = 45
    spacing = 7
    for i in range(10):
        rect_color = (255, 255, 255) if i < hp else (0, 0, 0)
        pygame.draw.rect(surface, rect_color, (hp_x + i*(hp_size+spacing), hp_y, hp_size, hp_size))
        pygame.draw.rect(surface, (255, 0, 0), (hp_x + i*(hp_size+spacing), hp_y, hp_size, hp_size), 2)

def get_highlight_color(key, current_time):
    t_stamp = square_highlights.get(key, 0)
    if t_stamp == 0:
        return (200, 200, 200)
    dt = current_time - t_stamp
    if dt < 200:
        val = 150 + int((50 * dt) / 200)
        return (val, val, val)
    else:
        return (200, 200, 200)

def draw_hit_error_bar(surface, hit_errors):
    lane_width = 200
    lane_height = 4
    lane_x = (w - lane_width) // 2
    lane_y = h - 60
    pygame.draw.line(surface, (255, 255, 255), (lane_x, lane_y), (lane_x + lane_width, lane_y), lane_height)
    
    if hit_errors:
        avg_error = sum(error for _, error in hit_errors) / len(hit_errors)
    else:
        avg_error = 0
    clamped_error = max(-50, min(50, avg_error))
    ratio = (clamped_error + 50) / 100.0
    triangle_x = lane_x + ratio * lane_width
    triangle_points = [(triangle_x, lane_y), (triangle_x - 5, lane_y - 10), (triangle_x + 5, lane_y - 10)]
    pygame.draw.polygon(surface, (255, 255, 0), triangle_points)
    
    avg_text = font.render(f"{avg_error:.0f}ms", True, (255,255,255))
    avg_text_rect = avg_text.get_rect(center=(w//2, lane_y - 20))
    surface.blit(avg_text, avg_text_rect)
    
    current_time = pygame.time.get_ticks()
    new_errors = []
    for marker in hit_errors:
        timestamp, error = marker
        dt = current_time - timestamp
        if dt > 10000:
            continue
        alpha = int(255 * (1 - dt / 10000))
        clamped_err = max(-50, min(50, error))
        ratio_err = (clamped_err + 50) / 100.0
        marker_x = lane_x + ratio_err * lane_width
        marker_y = lane_y + 10
        marker_surface = pygame.Surface((10, 2), pygame.SRCALPHA)
        marker_surface.fill((255, 255, 255, alpha))
        surface.blit(marker_surface, (marker_x - 5, marker_y))
        new_errors.append((timestamp, error))
    hit_errors[:] = new_errors


class Circle:
    def __init__(self, x, y, effective_shrink_time, label):
        self.x = x
        self.y = y
        self.clicked = False
        self.animating = False
        self.animation_start_time = None
        self.spawn_time = pygame.time.get_ticks()
        self.effective_shrink_time = effective_shrink_time
        self.missed = False
        self.label = label

    def draw(self, surface):
        global hp, attempts, circle_size_multiplier, combo
        current_time = pygame.time.get_ticks()
        effective_circle_radius = int(CIRCLE_RADIUS * circle_size_multiplier)
        effective_approach_radius = int(APPROACH_RADIUS * circle_size_multiplier)

        if self.animating:
            progress = (current_time - self.animation_start_time) / 300.0
            if progress < 1.0:
                new_radius = int(effective_circle_radius * (1 + 0.2 * progress))
                alpha = int(255 * (1 - progress))
                temp_surface = pygame.Surface((new_radius*2, new_radius*2), pygame.SRCALPHA)
                fading_color = (CIRCLE_COLOR[0], CIRCLE_COLOR[1], CIRCLE_COLOR[2], alpha)
                pygame.draw.circle(temp_surface, fading_color, (new_radius, new_radius), new_radius)
                outline_color = (0, 0, 0, alpha)
                pygame.draw.circle(temp_surface, outline_color, (new_radius, new_radius), new_radius, 2)
                scaled_font = pygame.font.Font(None, int(40 * circle_size_multiplier))
                counter_text = scaled_font.render(str(self.label), True, (255, 255, 255))
                counter_text.set_alpha(alpha)
                text_rect = counter_text.get_rect(center=(new_radius, new_radius))
                temp_surface.blit(counter_text, text_rect)
                surface.blit(temp_surface, (self.x - new_radius, self.y - new_radius))
            else:
                self.clicked = True
            return

        if self.clicked:
            return

        elapsed = current_time - self.spawn_time
        progress = elapsed / self.effective_shrink_time

        if progress >= 1:
            if not self.missed:
                self.missed = True
                hp = max(0, hp - 3)
                attempts += 1
                global combo
                combo = 0
            self.clicked = True
            return

        current_radius = effective_approach_radius - (effective_approach_radius - effective_circle_radius) * progress
        pygame.draw.circle(surface, APPROACH_COLOR, (self.x, self.y), int(current_radius), 2)
        pygame.draw.circle(surface, CIRCLE_COLOR, (self.x, self.y), effective_circle_radius)
        pygame.draw.circle(surface, (0, 0, 0), (self.x, self.y), effective_circle_radius, 2)
        scaled_font = pygame.font.Font(None, int(40 * circle_size_multiplier))
        counter_text = scaled_font.render(str(self.label), True, (255, 255, 255))
        text_rect = counter_text.get_rect(center=(self.x, self.y))
        surface.blit(counter_text, text_rect)


def spawn_circle(effective_shrink_time):
    global circle_spawn_counter, circles
    attempts_spawn = 0
    while attempts_spawn < 100:
        x = random.randint(spawn_area_x + CIRCLE_RADIUS, spawn_area_x + spawn_area_width - CIRCLE_RADIUS)
        y = random.randint(spawn_area_y + CIRCLE_RADIUS, spawn_area_y + spawn_area_height - CIRCLE_RADIUS)
        overlap = False
        for circle in circles:
            if not circle.clicked and math.hypot(circle.x - x, circle.y - y) < 2 * CIRCLE_RADIUS:
                overlap = True
                break
        if not overlap:
            break
        attempts_spawn += 1
    circle_spawn_counter += 1
    if circle_spawn_counter >= 100:
        circle_spawn_counter = 1
    return Circle(x, y, effective_shrink_time, circle_spawn_counter)


def save_map_data(map_data):
    root = tk.Tk()
    root.withdraw()  
    file_path = filedialog.asksaveasfilename(
        title="Save Map",
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if file_path:
        try:
            with open(file_path, "w") as f:
                json.dump(map_data, f, indent=4)
            print("Map saved to", file_path)
        except Exception as e:
            print("Error saving map:", e)
    root.destroy()


def import_map_file():
    global imported_map_filename
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select Map File",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if file_path:
        dest_folder = "maps"
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)
        base_name = os.path.basename(file_path)
        dest_path = os.path.join(dest_folder, base_name)
        try:
            shutil.copy(file_path, dest_path)
            imported_map_filename = base_name  
            print("Map imported to", dest_path)
        except Exception as e:
            print("Error importing map:", e)
    root.destroy()


def run_custom_map(map_data):
    map_data.sort(key=lambda event: event["time"])
    start_time = pygame.time.get_ticks()
    event_index = 0


    global score, hit_count, hp, trail_positions, circles, circle_spawn_counter, attempts
    global keybind1_count, keybind2_count, mouse_left_count, mouse_right_count, hit_errors
    global combo, combo_animation_start, accuracy_sum

    score = 0
    hit_count = 0
    attempts = 0
    hp = 10
    circles = []
    trail_positions = []
    circle_spawn_counter = 0
    keybind1_count = 0
    keybind2_count = 0
    mouse_left_count = 0
    mouse_right_count = 0
    hit_errors = []
    combo = 0
    combo_animation_start = 0
    accuracy_sum = 0

    effective_shrink_time = CIRCLE_SPAWN_TIME / speed_multiplier

    running = True
    while running:
        current_time = pygame.time.get_ticks()
        elapsed = current_time - start_time

        while event_index < len(map_data) and elapsed >= map_data[event_index]["time"]:
            event_item = map_data[event_index]
            new_circle = Circle(event_item["x"], event_item["y"], effective_shrink_time, event_item["label"])
            circles.append(new_circle)
            event_index += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    return
                elif event.key == pygame.K_BACKSLASH:
                    hp = 0
                if event.key == click_key1:
                    keybind1_count += 1
                    square_highlights["keybind1"] = current_time
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    click_time = pygame.time.get_ticks()
                    for circle in circles:
                        if (not circle.clicked and not circle.animating and
                            math.hypot(circle.x - mouse_x, circle.y - mouse_y) <= int(CIRCLE_RADIUS * circle_size_multiplier)):
                            circle.animating = True
                            circle.animation_start_time = click_time
                            hit_count += 1
                            attempts += 1
                            error = click_time - (circle.spawn_time + effective_shrink_time - 100)
                            hit_errors.append((click_time, error))
                            if (effective_shrink_time - (click_time - circle.spawn_time)) <= 200:
                                base_points = 300
                                if hp < 10:
                                    hp = min(10, hp + 1)
                                accuracy_sum += 100
                            elif (effective_shrink_time - (click_time - circle.spawn_time)) > 500:
                                base_points = 100
                                hp = max(0, hp - 1)
                                accuracy_sum += 20
                            else:
                                base_points = 200
                                accuracy_sum += 33
                            score += int(base_points * (1 + 0.1 * combo))
                            combo += 1
                            combo_animation_start = click_time
                            hit_sound.play()
                            break
                elif event.key == click_key2:
                    keybind2_count += 1
                    square_highlights["keybind2"] = current_time
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    click_time = pygame.time.get_ticks()
                    for circle in circles:
                        if (not circle.clicked and not circle.animating and
                            math.hypot(circle.x - mouse_x, circle.y - mouse_y) <= int(CIRCLE_RADIUS * circle_size_multiplier)):
                            circle.animating = True
                            circle.animation_start_time = click_time
                            hit_count += 1
                            attempts += 1
                            error = click_time - (circle.spawn_time + effective_shrink_time - 100)
                            hit_errors.append((click_time, error))
                            if (effective_shrink_time - (click_time - circle.spawn_time)) <= 200:
                                base_points = 300
                                if hp < 10:
                                    hp = min(10, hp + 1)
                                accuracy_sum += 100
                            elif (effective_shrink_time - (click_time - circle.spawn_time)) > 500:
                                base_points = 100
                                hp = max(0, hp - 1)
                                accuracy_sum += 20
                            else:
                                base_points = 200
                                accuracy_sum += 33
                            score += int(base_points * (1 + 0.1 * combo))
                            combo += 1
                            combo_animation_start = click_time
                            hit_sound.play()
                            break
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button in [4,5]:
                    continue
                if not disable_mouse:
                    if event.button == 1:
                        mouse_left_count += 1
                        square_highlights["mouse_left"] = current_time
                        mouse_x, mouse_y = pygame.mouse.get_pos()
                        click_time = pygame.time.get_ticks()
                        for circle in circles:
                            if (not circle.clicked and not circle.animating and
                                math.hypot(circle.x - mouse_x, circle.y - mouse_y) <= int(CIRCLE_RADIUS * circle_size_multiplier)):
                                circle.animating = True
                                circle.animation_start_time = click_time
                                hit_count += 1
                                attempts += 1
                                error = click_time - (circle.spawn_time + effective_shrink_time - 100)
                                hit_errors.append((click_time, error))
                                if (effective_shrink_time - (click_time - circle.spawn_time)) <= 200:
                                    base_points = 300
                                    if hp < 10:
                                        hp = min(10, hp + 1)
                                    accuracy_sum += 100
                                elif (effective_shrink_time - (click_time - circle.spawn_time)) > 500:
                                    base_points = 100
                                    hp = max(0, hp - 1)
                                    accuracy_sum += 20
                                else:
                                    base_points = 200
                                    accuracy_sum += 33
                                score += int(base_points * (1 + 0.1 * combo))
                                combo += 1
                                combo_animation_start = click_time
                                hit_sound.play()
                                break
                    elif event.button == 3:
                        mouse_right_count += 1
                        square_highlights["mouse_right"] = current_time
                        mouse_x, mouse_y = pygame.mouse.get_pos()
                        click_time = pygame.time.get_ticks()
                        for circle in circles:
                            if (not circle.clicked and not circle.animating and
                                math.hypot(circle.x - mouse_x, circle.y - mouse_y) <= int(CIRCLE_RADIUS * circle_size_multiplier)):
                                circle.animating = True
                                circle.animation_start_time = click_time
                                hit_count += 1
                                attempts += 1
                                error = click_time - (circle.spawn_time + effective_shrink_time - 100)
                                hit_errors.append((click_time, error))
                                if (effective_shrink_time - (click_time - circle.spawn_time)) <= 200:
                                    base_points = 300
                                    if hp < 10:
                                        hp = min(10, hp + 1)
                                    accuracy_sum += 100
                                elif (effective_shrink_time - (click_time - circle.spawn_time)) > 500:
                                    base_points = 100
                                    hp = max(0, hp - 1)
                                    accuracy_sum += 20
                                else:
                                    base_points = 200
                                    accuracy_sum += 33
                                score += int(base_points * (1 + 0.1 * combo))
                                combo += 1
                                combo_animation_start = click_time
                                hit_sound.play()
                                break


        mouse_x, mouse_y = pygame.mouse.get_pos()
        rect.center = (mouse_x, mouse_y)
        trail_positions.append((mouse_x, mouse_y, pygame.time.get_ticks()))


        if saved_slider3_value == 0:
            screen.fill((0, 0, 0))
        else:
            bg = pygame.transform.smoothscale(tlo, (w, h))
            screen.blit(bg, (0, 0))
            overlay_alpha = int((100 - saved_slider3_value) / 100 * 255)
            if overlay_alpha > 0:
                overlay.set_alpha(overlay_alpha)
                screen.blit(overlay, (0, 0))


        for pos in trail_positions:
            x, y, timestamp = pos
            if current_time - timestamp <= 70:
                pygame.draw.circle(screen, trail_color, (x, y), trail_size)


        for circle in circles:
            circle.draw(screen)
        circles = [circle for circle in circles if not circle.clicked]


        screen.blit(celownik, rect)


        overall_accuracy = (accuracy_sum / hit_count) if hit_count > 0 else 0
        overall_accuracy = min(overall_accuracy, 100)
        display_text = f"Score: {score}   Accuracy: {overall_accuracy:.2f}%"
        score_text = font.render(display_text, True, (255,255,255))
        text_rect = score_text.get_rect(topright=(w - 20, 20))
        pygame.draw.rect(screen, (0,0,0), text_rect)
        screen.blit(score_text, text_rect)

        if combo > 0:
            elapsed_combo = current_time - combo_animation_start
            if elapsed_combo < 250:
                if elapsed_combo < 125:
                    scale = 1 + 0.4 * (elapsed_combo / 125)
                else:
                    scale = 1.4 - 0.4 * ((elapsed_combo - 125) / 125)
            else:
                scale = 1
        else:
            scale = 1
        base_font_size = 60
        combo_font = pygame.font.Font(None, int(base_font_size * scale))
        combo_text = f"{combo}x"
        combo_surface = combo_font.render(combo_text, True, (255, 255, 255))
        combo_rect = combo_surface.get_rect(bottomleft=(20, h - 20))
        screen.blit(combo_surface, combo_rect)

        draw_hp_bar(screen, hp)
        pygame.draw.rect(screen, (255,255,255), (spawn_area_x, spawn_area_y, spawn_area_width, spawn_area_height), 2)


        square_width = 50
        square_height = 50
        spacing = 10
        total_height = 4 * square_height + 3 * spacing
        y_square_start = (h - total_height) // 2
        x_square = w - square_width - 20
        padding = 5

        col1 = get_highlight_color("keybind1", current_time)
        rect1 = pygame.Rect(x_square, y_square_start, square_width, square_height)
        rect1_black = pygame.Rect(rect1.x - padding, rect1.y - padding, rect1.width + 2*padding, rect1.height + 2*padding)
        pygame.draw.rect(screen, (0,0,0), rect1_black)
        pygame.draw.rect(screen, col1, rect1)
        pygame.draw.rect(screen, (255,0,0), rect1, 2)
        keybind1_text_disp = small_font.render(str(keybind1_count), True, (255,255,255))
        text_rect1 = keybind1_text_disp.get_rect(center=rect1.center)
        screen.blit(keybind1_text_disp, text_rect1)

        col2 = get_highlight_color("keybind2", current_time)
        rect2 = pygame.Rect(x_square, y_square_start + square_height + spacing, square_width, square_height)
        rect2_black = pygame.Rect(rect2.x - padding, rect2.y - padding, rect2.width + 2*padding, rect2.height + 2*padding)
        pygame.draw.rect(screen, (0,0,0), rect2_black)
        pygame.draw.rect(screen, col2, rect2)
        pygame.draw.rect(screen, (255,0,0), rect2, 2)
        keybind2_text_disp = small_font.render(str(keybind2_count), True, (255,255,255))
        text_rect2 = keybind2_text_disp.get_rect(center=rect2.center)
        screen.blit(keybind2_text_disp, text_rect2)

        col3 = get_highlight_color("mouse_left", current_time) if not disable_mouse else (200,200,200)
        rect3 = pygame.Rect(x_square, y_square_start + 2*(square_height + spacing), square_width, square_height)
        rect3_black = pygame.Rect(rect3.x - padding, rect3.y - padding, rect3.width + 2*padding, rect3.height + 2*padding)
        pygame.draw.rect(screen, (0,0,0), rect3_black)
        pygame.draw.rect(screen, col3, rect3)
        pygame.draw.rect(screen, (255,0,0), rect3, 2)
        ml_count = 0 if disable_mouse else mouse_left_count
        mouse_left_text_disp = small_font.render(str(ml_count), True, (255,255,255))
        text_rect3 = mouse_left_text_disp.get_rect(center=rect3.center)
        screen.blit(mouse_left_text_disp, text_rect3)

        col4 = get_highlight_color("mouse_right", current_time) if not disable_mouse else (200,200,200)
        rect4 = pygame.Rect(x_square, y_square_start + 3*(square_height + spacing), square_width, square_height)
        rect4_black = pygame.Rect(rect4.x - padding, rect4.y - padding, rect4.width + 2*padding, rect4.height + 2*padding)
        pygame.draw.rect(screen, (0,0,0), rect4_black)
        pygame.draw.rect(screen, col4, rect4)
        pygame.draw.rect(screen, (255,0,0), rect4, 2)
        mr_count = 0 if disable_mouse else mouse_right_count
        mouse_right_text_disp = small_font.render(str(mr_count), True, (255,255,255))
        text_rect4 = mouse_right_text_disp.get_rect(center=rect4.center)
        screen.blit(mouse_right_text_disp, text_rect4)

        draw_hit_error_bar(screen, hit_errors)

        if hp <= 0:
            game_over_text = font.render("GAME OVER", True, (255,0,0))
            game_over_rect = game_over_text.get_rect(center=(w//2, h//2))
            screen.blit(game_over_text, game_over_rect)
            pygame.display.flip()
            pygame.time.delay(2000)
            return

        pygame.display.flip()
        clock.tick(120)


def run_settings():
    global saved_slider3_value, click_key1, click_key2, selected_keybind, disable_mouse
    pygame.mouse.set_visible(True)
    settings = True

    button_width = 300
    button_height = 75
    back_button = pygame.Rect((w - button_width) // 2, h - button_height - 50, button_width, button_height)

    slider3_width = 450
    slider3_height = 15
    slider3_x = w // 2 - slider3_width // 2
    slider3_y = 250

    keybind1_rect = pygame.Rect(w // 2 - 150, slider3_y + 80, 120, 50)
    keybind2_rect = pygame.Rect(w // 2 + 30, slider3_y + 80, 120, 50)
    disable_mouse_rect = pygame.Rect(w//2 - 150, slider3_y + 160, 300, 50)

    min_slider3, max_slider3 = 0, 100
    step3 = slider3_width / (max_slider3 - min_slider3)
    slider3_value = saved_slider3_value

    dragging3 = False

    while settings:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit(); exit()
            if selected_keybind is not None and event.type == pygame.KEYDOWN:
                if selected_keybind == 1:
                    click_key1 = event.key
                elif selected_keybind == 2:
                    click_key2 = event.key
                selected_keybind = None
            if event.type == MOUSEBUTTONDOWN:
                mouse_x, mouse_y = event.pos
                if back_button.collidepoint(mouse_x, mouse_y):
                    settings = False
                if keybind1_rect.collidepoint(mouse_x, mouse_y):
                    selected_keybind = 1
                if keybind2_rect.collidepoint(mouse_x, mouse_y):
                    selected_keybind = 2
                if disable_mouse_rect.collidepoint(mouse_x, mouse_y):
                    disable_mouse = not disable_mouse
                knob3_x = slider3_x + (slider3_value - min_slider3) * step3
                knob3_y = slider3_y + slider3_height // 2
                if math.hypot(mouse_x - knob3_x, mouse_y - knob3_y) <= 22:
                    dragging3 = True
            if event.type == MOUSEBUTTONUP:
                dragging3 = False
            if event.type == MOUSEMOTION:
                mouse_x, _ = event.pos
                if dragging3:
                    mouse_x = max(slider3_x, min(mouse_x, slider3_x + slider3_width))
                    slider3_value = round(min_slider3 + (mouse_x - slider3_x) / step3)
                    saved_slider3_value = slider3_value

        screen.fill((50, 50, 50))
        settings_title = title_font.render("SETTINGS", True, (255, 255, 255))
        settings_title_rect = settings_title.get_rect(center=(w//2, 100))
        screen.blit(settings_title, settings_title_rect)

        pygame.draw.rect(screen, (200,200,200), (slider3_x, slider3_y, slider3_width, slider3_height))
        knob3_x = slider3_x + (slider3_value - min_slider3) * step3
        knob3_y = slider3_y + slider3_height // 2
        pygame.draw.circle(screen, (0,0,255), (int(knob3_x), int(knob3_y)), 22)
        bgdim_text = font.render(f"Background Dim: {slider3_value}%", True, (255,255,255))
        bgdim_rect = bgdim_text.get_rect(center=(w//2, slider3_y - 30))
        screen.blit(bgdim_text, bgdim_rect)

        keybind1_text = font.render("Keybind 1: " + pygame.key.name(click_key1), True, (255,255,255))
        pygame.draw.rect(screen, (100,100,100), keybind1_rect)
        screen.blit(keybind1_text, keybind1_text.get_rect(center=keybind1_rect.center))

        keybind2_text = font.render("Keybind 2: " + pygame.key.name(click_key2), True, (255,255,255))
        pygame.draw.rect(screen, (100,100,100), keybind2_rect)
        screen.blit(keybind2_text, keybind2_text.get_rect(center=keybind2_rect.center))

        disable_text = "Disable Mouse: ON" if disable_mouse else "Disable Mouse: OFF"
        disable_button = pygame.Rect(w//2 - 150, slider3_y + 160, 300, 50)
        pygame.draw.rect(screen, (100,100,100), disable_button)
        pygame.draw.rect(screen, (255,0,0), disable_button, 2)
        disable_text_render = font.render(disable_text, True, (255,255,255))
        disable_text_rect = disable_text_render.get_rect(center=disable_button.center)
        screen.blit(disable_text_render, disable_text_rect)

        pygame.draw.rect(screen, (0,0,0), back_button)
        pygame.draw.rect(screen, (255,0,0), back_button, 2)
        back_text = font.render("Back", True, (255,255,255))
        screen.blit(back_text, back_text.get_rect(center=back_button.center))

        if selected_keybind is not None:
            popup_text = font.render("Press a key to set keybind", True, (255,255,255))
            popup_rect = popup_text.get_rect(center=(w//2, h - 150))
            screen.blit(popup_text, popup_rect)

        pygame.display.flip()
        clock.tick(60)


def run_mods():
    global saved_slider1_value, saved_slider2_value, saved_circle_size_multiplier
    global speed_multiplier, spawn_multiplier, circle_size_multiplier

    pygame.mouse.set_visible(True)
    mods_running = True

    slider1_width = 450
    slider1_height = 15
    slider1_x = w // 2 - slider1_width // 2
    slider1_y = 150

    slider2_width = 450
    slider2_height = 15
    slider2_x = w // 2 - slider2_width // 2
    slider2_y = slider1_y + 80

    slider3_width = 450
    slider3_height = 15
    slider3_x = w // 2 - slider3_width // 2
    slider3_y = slider2_y + 80

    min_slider1, max_slider1 = 1, 10   
    min_slider2, max_slider2 = 1, 15   
    min_slider3, max_slider3 = 10, 25   

    step1 = slider1_width / (max_slider1 - min_slider1)
    step2 = slider2_width / (max_slider2 - min_slider2)
    step3 = slider3_width / (max_slider3 - min_slider3)

    slider1_value = saved_slider1_value
    slider2_value = saved_slider2_value
    slider3_value = saved_circle_size_multiplier

    dragging1 = dragging2 = dragging3 = False

    back_button = pygame.Rect((w - 300) // 2, h - 100, 300, 75)

    while mods_running:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit(); exit()
            if event.type == MOUSEBUTTONDOWN:
                mouse_x, mouse_y = event.pos
                if back_button.collidepoint(mouse_x, mouse_y):
                    mods_running = False
                knob1_x = slider1_x + (slider1_value - min_slider1) * step1
                knob1_y = slider1_y + slider1_height // 2
                if math.hypot(mouse_x - knob1_x, mouse_y - knob1_y) <= 22:
                    dragging1 = True
                knob2_x = slider2_x + (slider2_value - min_slider2) * step2
                knob2_y = slider2_y + slider2_height // 2
                if math.hypot(mouse_x - knob2_x, mouse_y - knob2_y) <= 22:
                    dragging2 = True
                knob3_x = slider3_x + (slider3_value - min_slider3) * step3
                knob3_y = slider3_y + slider3_height // 2
                if math.hypot(mouse_x - knob3_x, mouse_y - knob3_y) <= 22:
                    dragging3 = True
            if event.type == MOUSEBUTTONUP:
                dragging1 = dragging2 = dragging3 = False
            if event.type == MOUSEMOTION:
                mouse_x, _ = event.pos
                if dragging1:
                    mouse_x = max(slider1_x, min(mouse_x, slider1_x + slider1_width))
                    slider1_value = round(min_slider1 + (mouse_x - slider1_x) / step1)
                    saved_slider1_value = slider1_value
                    speed_multiplier = 1 + (slider1_value - min_slider1) * 0.2
                if dragging2:
                    mouse_x = max(slider2_x, min(mouse_x, slider2_x + slider2_width))
                    slider2_value = round(min_slider2 + (mouse_x - slider2_x) / step2)
                    saved_slider2_value = slider2_value
                    spawn_multiplier = 1 + (slider2_value - min_slider2) * 0.2
                if dragging3:
                    mouse_x = max(slider3_x, min(mouse_x, slider3_x + slider3_width))
                    slider3_value = round(min_slider3 + (mouse_x - slider3_x) / step3)
                    saved_circle_size_multiplier = slider3_value
                    circle_size_multiplier = slider3_value / 10.0

        screen.fill((50, 50, 50))
        mods_title = title_font.render("MODS", True, (255,255,255))
        mods_title_rect = mods_title.get_rect(center=(w//2, 80))
        screen.blit(mods_title, mods_title_rect)

        pygame.draw.rect(screen, (200,200,200), (slider1_x, slider1_y, slider1_width, slider1_height))
        knob1_x = slider1_x + (slider1_value - min_slider1) * step1
        knob1_y = slider1_y + slider1_height // 2
        pygame.draw.circle(screen, (255,0,0), (int(knob1_x), int(knob1_y)), 22)
        approach_text = font.render(f"Approach Rate: {1 + (slider1_value - min_slider1)*0.2:.1f}x", True, (255,255,255))
        approach_rect = approach_text.get_rect(center=(w//2, slider1_y - 30))
        screen.blit(approach_text, approach_rect)

        pygame.draw.rect(screen, (200,200,200), (slider2_x, slider2_y, slider2_width, slider2_height))
        knob2_x = slider2_x + (slider2_value - min_slider2) * step2
        knob2_y = slider2_y + slider2_height // 2
        pygame.draw.circle(screen, (0,255,0), (int(knob2_x), int(knob2_y)), 22)
        spawn_text = font.render(f"Spawn Rate: {1 + (slider2_value - min_slider2)*0.2:.1f}x", True, (255,255,255))
        spawn_rect = spawn_text.get_rect(center=(w//2, slider2_y - 30))
        screen.blit(spawn_text, spawn_rect)

        pygame.draw.rect(screen, (200,200,200), (slider3_x, slider3_y, slider3_width, slider3_height))
        knob3_x = slider3_x + (slider3_value - min_slider3) * step3
        knob3_y = slider3_y + slider3_height // 2
        pygame.draw.circle(screen, (0,128,255), (int(knob3_x), int(knob3_y)), 22)
        circlesize_text = font.render(f"Circle Size: {circle_size_multiplier:.1f}x", True, (255,255,255))
        circlesize_rect = circlesize_text.get_rect(center=(w//2, slider3_y - 30))
        screen.blit(circlesize_text, circlesize_rect)

        pygame.draw.rect(screen, (0,0,0), back_button)
        pygame.draw.rect(screen, (255,0,0), back_button, 2)
        back_text = font.render("Back", True, (255,255,255))
        screen.blit(back_text, back_text.get_rect(center=back_button.center))

        pygame.display.flip()
        clock.tick(60)


def run_map_picker():
    running = True
    random_rect = pygame.Rect(w - 350, h//2 - 50, 300, 100)
    back_button = pygame.Rect(20, h - 70, 150, 50)
    imported_rect = None
    if imported_map_filename:
        display_name = os.path.splitext(imported_map_filename)[0]
        imported_rect = pygame.Rect(w - 350, h//2 + 70, 300, 100)
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = event.pos
                if random_rect.collidepoint(mouse_x, mouse_y):
                    return "start"
                if back_button.collidepoint(mouse_x, mouse_y):
                    return "back"
                if imported_rect and imported_rect.collidepoint(mouse_x, mouse_y):
                    map_path = os.path.join("maps", imported_map_filename)
                    try:
                        with open(map_path, "r") as f:
                            map_data = json.load(f)
                        run_custom_map(map_data)
                    except Exception as e:
                        print("Error loading custom map:", e)
        screen.fill((0, 0, 0))
        title = title_font.render("Map Picker", True, (255,255,255))
        title_rect = title.get_rect(center=(w//2, 100))
        screen.blit(title, title_rect)
        pygame.draw.rect(screen, (255,255,255), random_rect)
        pygame.draw.rect(screen, (0,0,0), random_rect, 2)
        random_text = font.render("RANDOM", True, (0,0,0))
        text_rect = random_text.get_rect(center=random_rect.center)
        screen.blit(random_text, text_rect)
        pygame.draw.rect(screen, (0,0,0), back_button)
        pygame.draw.rect(screen, (255,0,0), back_button, 2)
        back_text = font.render("Back", True, (255,255,255))
        screen.blit(back_text, back_text.get_rect(center=back_button.center))
        if imported_rect:
            pygame.draw.rect(screen, (255,255,255), imported_rect)
            pygame.draw.rect(screen, (0,0,0), imported_rect, 2)
            imported_text = font.render(display_name, True, (0,0,0))
            imported_text_rect = imported_text.get_rect(center=imported_rect.center)
            screen.blit(imported_text, imported_text_rect)
        mods_rect = mods_img.get_rect(center=(w//2, h - 100))
        screen.blit(mods_img, mods_rect)
        pygame.display.flip()
        clock.tick(60)


def run_map_maker():
    pygame.mouse.set_visible(True)
    running = True
    map_data = []
    event_counter = 1
    map_elapsed_time = 0
    last_time = pygame.time.get_ticks()
    paused = False

    save_button = pygame.Rect(w - 180, h - 70, 150, 50)
    load_button = pygame.Rect(w - 180, h - 140, 150, 50)
    play_button = pygame.Rect(w - 180, h - 210, 150, 50)
    back_button = pygame.Rect(20, h - 70, 150, 50)

    while running:
        current_time = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = event.pos
                if (spawn_area_x <= mouse_x <= spawn_area_x + spawn_area_width and
                    spawn_area_y <= mouse_y <= spawn_area_y + spawn_area_height):
                    map_event = {
                        "time": map_elapsed_time,
                        "x": mouse_x,
                        "y": mouse_y,
                        "label": event_counter
                    }
                    map_data.append(map_event)
                    event_counter += 1
                if save_button.collidepoint(mouse_x, mouse_y):
                    save_map_data(map_data)
                if load_button.collidepoint(mouse_x, mouse_y):
                    try:
                        with open("maps/maps.json", "r") as f:
                            map_data = json.load(f)
                        if map_data:
                            event_counter = max(event["label"] for event in map_data) + 1
                        else:
                            event_counter = 1
                        print("Map loaded.")
                    except Exception as e:
                        print("Load error:", e)
                if play_button.collidepoint(mouse_x, mouse_y):
                    run_custom_map(map_data)
                if back_button.collidepoint(mouse_x, mouse_y):
                    running = False

        if not paused:
            dt = current_time - last_time
            map_elapsed_time += dt * 0.6
        last_time = current_time

        screen.fill((30, 30, 30))
        title = title_font.render("Map Maker", True, (255,255,255))
        title_rect = title.get_rect(center=(w//2, 100))
        screen.blit(title, title_rect)
        pygame.draw.rect(screen, (100,100,100), (spawn_area_x, spawn_area_y, spawn_area_width, spawn_area_height), 2)
        info_text = font.render("Click inside the area to add circle events.", True, (255,255,255))
        screen.blit(info_text, (spawn_area_x, spawn_area_y - 30))
        for event_item in map_data:
            pygame.draw.circle(screen, CIRCLE_COLOR, (event_item["x"], event_item["y"]), CIRCLE_RADIUS)
            label_text = font.render(str(event_item["label"]), True, (255,255,255))
            label_rect = label_text.get_rect(center=(event_item["x"], event_item["y"]))
            screen.blit(label_text, label_rect)
        pygame.draw.rect(screen, (100,100,100), save_button)
        pygame.draw.rect(screen, (255,0,0), save_button, 2)
        save_text = font.render("Save", True, (255,255,255))
        screen.blit(save_text, save_text.get_rect(center=save_button.center))
        pygame.draw.rect(screen, (100,100,100), load_button)
        pygame.draw.rect(screen, (255,0,0), load_button, 2)
        load_text = font.render("Load", True, (255,255,255))
        screen.blit(load_text, load_text.get_rect(center=load_button.center))
        pygame.draw.rect(screen, (100,100,100), play_button)
        pygame.draw.rect(screen, (255,0,0), play_button, 2)
        play_text = font.render("Play Map", True, (255,255,255))
        screen.blit(play_text, play_text.get_rect(center=play_button.center))
        pygame.draw.rect(screen, (100,100,100), back_button)
        pygame.draw.rect(screen, (255,0,0), back_button, 2)
        back_text = font.render("Back", True, (255,255,255))
        screen.blit(back_text, back_text.get_rect(center=back_button.center))
        time_text = font.render(f"Time: {int(map_elapsed_time)}ms", True, (255,255,255))
        screen.blit(time_text, (spawn_area_x, spawn_area_y + spawn_area_height + 10))
        status_text = font.render("Paused" if paused else "Running", True, (255,255,255))
        screen.blit(status_text, (spawn_area_x + 200, spawn_area_y + spawn_area_height + 10))
        pygame.display.flip()
        clock.tick(60)


def run_game():
    global score, hit_count, hp, trail_positions, circles, circle_spawn_counter, attempts
    global click_key1, click_key2, keybind1_count, keybind2_count, mouse_left_count, mouse_right_count, hit_errors
    global combo, combo_animation_start, accuracy_sum
    score = 0
    hit_count = 0
    attempts = 0
    hp = 10
    circles = []
    trail_positions = []
    circle_spawn_counter = 0
    keybind1_count = 0
    keybind2_count = 0
    mouse_left_count = 0
    mouse_right_count = 0
    hit_errors = []
    combo = 0
    combo_animation_start = 0
    accuracy_sum = 0

    effective_shrink_time = CIRCLE_SPAWN_TIME / speed_multiplier
    effective_spawn_interval = CIRCLE_SPAWN_TIME / spawn_multiplier
    last_spawn_time = pygame.time.get_ticks()
    
    pygame.mouse.set_visible(False)
    
    while True:
        current_time = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    return
                elif event.key == pygame.K_BACKSLASH:
                    hp = 0
                if event.key == click_key1:
                    keybind1_count += 1
                    square_highlights["keybind1"] = current_time
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    click_time = pygame.time.get_ticks()
                    for circle in circles:
                        if (not circle.clicked and not circle.animating and
                            math.hypot(circle.x - mouse_x, circle.y - mouse_y) <= int(CIRCLE_RADIUS * circle_size_multiplier)):
                            circle.animating = True
                            circle.animation_start_time = click_time
                            hit_count += 1
                            attempts += 1
                            error = click_time - (circle.spawn_time + effective_shrink_time - 100)
                            hit_errors.append((click_time, error))
                            if (effective_shrink_time - (click_time - circle.spawn_time)) <= 200:
                                base_points = 300
                                if hp < 10:
                                    hp = min(10, hp + 1)
                                accuracy_sum += 100
                            elif (effective_shrink_time - (click_time - circle.spawn_time)) > 500:
                                base_points = 100
                                hp = max(0, hp - 1)
                                accuracy_sum += 20
                            else:
                                base_points = 200
                                accuracy_sum += 33
                            score += int(base_points * (1 + 0.1 * combo))
                            combo += 1
                            combo_animation_start = click_time
                            hit_sound.play()
                            break
                elif event.key == click_key2:
                    keybind2_count += 1
                    square_highlights["keybind2"] = current_time
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    click_time = pygame.time.get_ticks()
                    for circle in circles:
                        if (not circle.clicked and not circle.animating and
                            math.hypot(circle.x - mouse_x, circle.y - mouse_y) <= int(CIRCLE_RADIUS * circle_size_multiplier)):
                            circle.animating = True
                            circle.animation_start_time = click_time
                            hit_count += 1
                            attempts += 1
                            error = click_time - (circle.spawn_time + effective_shrink_time - 100)
                            hit_errors.append((click_time, error))
                            if (effective_shrink_time - (click_time - circle.spawn_time)) <= 200:
                                base_points = 300
                                if hp < 10:
                                    hp = min(10, hp + 1)
                                accuracy_sum += 100
                            elif (effective_shrink_time - (click_time - circle.spawn_time)) > 500:
                                base_points = 100
                                hp = max(0, hp - 1)
                                accuracy_sum += 20
                            else:
                                base_points = 200
                                accuracy_sum += 33
                            score += int(base_points * (1 + 0.1 * combo))
                            combo += 1
                            combo_animation_start = click_time
                            hit_sound.play()
                            break
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button in [4,5]:
                    continue
                if not disable_mouse:
                    if event.button == 1:
                        mouse_left_count += 1
                        square_highlights["mouse_left"] = current_time
                        mouse_x, mouse_y = pygame.mouse.get_pos()
                        click_time = pygame.time.get_ticks()
                        for circle in circles:
                            if (not circle.clicked and not circle.animating and
                                math.hypot(circle.x - mouse_x, circle.y - mouse_y) <= int(CIRCLE_RADIUS * circle_size_multiplier)):
                                circle.animating = True
                                circle.animation_start_time = click_time
                                hit_count += 1
                                attempts += 1
                                error = click_time - (circle.spawn_time + effective_shrink_time - 100)
                                hit_errors.append((click_time, error))
                                if (effective_shrink_time - (click_time - circle.spawn_time)) <= 200:
                                    base_points = 300
                                    if hp < 10:
                                        hp = min(10, hp + 1)
                                    accuracy_sum += 100
                                elif (effective_shrink_time - (click_time - circle.spawn_time)) > 500:
                                    base_points = 100
                                    hp = max(0, hp - 1)
                                    accuracy_sum += 20
                                else:
                                    base_points = 200
                                    accuracy_sum += 33
                                score += int(base_points * (1 + 0.1 * combo))
                                combo += 1
                                combo_animation_start = click_time
                                hit_sound.play()
                                break
                    elif event.button == 3:
                        mouse_right_count += 1
                        square_highlights["mouse_right"] = current_time
                        mouse_x, mouse_y = pygame.mouse.get_pos()
                        click_time = pygame.time.get_ticks()
                        for circle in circles:
                            if (not circle.clicked and not circle.animating and
                                math.hypot(circle.x - mouse_x, circle.y - mouse_y) <= int(CIRCLE_RADIUS * circle_size_multiplier)):
                                circle.animating = True
                                circle.animation_start_time = click_time
                                hit_count += 1
                                attempts += 1
                                error = click_time - (circle.spawn_time + effective_shrink_time - 100)
                                hit_errors.append((click_time, error))
                                if (effective_shrink_time - (click_time - circle.spawn_time)) <= 200:
                                    base_points = 300
                                    if hp < 10:
                                        hp = min(10, hp + 1)
                                    accuracy_sum += 100
                                elif (effective_shrink_time - (click_time - circle.spawn_time)) > 500:
                                    base_points = 100
                                    hp = max(0, hp - 1)
                                    accuracy_sum += 20
                                else:
                                    base_points = 200
                                    accuracy_sum += 33
                                score += int(base_points * (1 + 0.1 * combo))
                                combo += 1
                                combo_animation_start = click_time
                                hit_sound.play()
                                break
        
        mouse_x, mouse_y = pygame.mouse.get_pos()
        rect.center = (mouse_x, mouse_y)
        trail_positions.append((mouse_x, mouse_y, pygame.time.get_ticks()))
        current_time = pygame.time.get_ticks()
        if current_time - last_spawn_time > effective_spawn_interval:
            circles.append(spawn_circle(effective_shrink_time))
            last_spawn_time = current_time
        
        if saved_slider3_value == 0:
            screen.fill((0, 0, 0))
        else:
            bg = pygame.transform.smoothscale(tlo, (w, h))
            screen.blit(bg, (0, 0))
            overlay_alpha = int((100 - saved_slider3_value) / 100 * 255)
            if overlay_alpha > 0:
                overlay.set_alpha(overlay_alpha)
                screen.blit(overlay, (0, 0))
        
        for pos in trail_positions:
            x, y, timestamp = pos
            if current_time - timestamp <= 70:
                pygame.draw.circle(screen, trail_color, (x, y), trail_size)
        
        for circle in circles:
            circle.draw(screen)
        circles = [circle for circle in circles if not circle.clicked]
        screen.blit(celownik, rect)
        overall_accuracy = (accuracy_sum / hit_count) if hit_count > 0 else 0
        overall_accuracy = min(overall_accuracy, 100)
        display_text = f"Score: {score}   Accuracy: {overall_accuracy:.2f}%"
        score_text = font.render(display_text, True, (255,255,255))
        text_rect = score_text.get_rect(topright=(w - 20, 20))
        pygame.draw.rect(screen, (0,0,0), text_rect)
        screen.blit(score_text, text_rect)
        if combo > 0:
            elapsed_combo = current_time - combo_animation_start
            if elapsed_combo < 250:
                if elapsed_combo < 125:
                    scale = 1 + 0.4 * (elapsed_combo / 125)
                else:
                    scale = 1.4 - 0.4 * ((elapsed_combo - 125) / 125)
            else:
                scale = 1
        else:
            scale = 1
        base_font_size = 60
        combo_font = pygame.font.Font(None, int(base_font_size * scale))
        combo_text = f"{combo}x"
        combo_surface = combo_font.render(combo_text, True, (255, 255, 255))
        combo_rect = combo_surface.get_rect(bottomleft=(20, h - 20))
        screen.blit(combo_surface, combo_rect)
        draw_hp_bar(screen, hp)
        pygame.draw.rect(screen, (255,255,255), (spawn_area_x, spawn_area_y, spawn_area_width, spawn_area_height), 2)
        square_width = 50
        square_height = 50
        spacing = 10
        total_height = 4 * square_height + 3 * spacing
        y_square_start = (h - total_height) // 2
        x_square = w - square_width - 20
        padding = 5
        col1 = get_highlight_color("keybind1", current_time)
        rect1 = pygame.Rect(x_square, y_square_start, square_width, square_height)
        rect1_black = pygame.Rect(rect1.x - padding, rect1.y - padding, rect1.width + 2*padding, rect1.height + 2*padding)
        pygame.draw.rect(screen, (0,0,0), rect1_black)
        pygame.draw.rect(screen, col1, rect1)
        pygame.draw.rect(screen, (255,0,0), rect1, 2)
        keybind1_text_disp = small_font.render(str(keybind1_count), True, (255,255,255))
        text_rect1 = keybind1_text_disp.get_rect(center=rect1.center)
        screen.blit(keybind1_text_disp, text_rect1)
        col2 = get_highlight_color("keybind2", current_time)
        rect2 = pygame.Rect(x_square, y_square_start + square_height + spacing, square_width, square_height)
        rect2_black = pygame.Rect(rect2.x - padding, rect2.y - padding, rect2.width + 2*padding, rect2.height + 2*padding)
        pygame.draw.rect(screen, (0,0,0), rect2_black)
        pygame.draw.rect(screen, col2, rect2)
        pygame.draw.rect(screen, (255,0,0), rect2, 2)
        keybind2_text_disp = small_font.render(str(keybind2_count), True, (255,255,255))
        text_rect2 = keybind2_text_disp.get_rect(center=rect2.center)
        screen.blit(keybind2_text_disp, text_rect2)
        col3 = get_highlight_color("mouse_left", current_time) if not disable_mouse else (200,200,200)
        rect3 = pygame.Rect(x_square, y_square_start + 2*(square_height + spacing), square_width, square_height)
        rect3_black = pygame.Rect(rect3.x - padding, rect3.y - padding, rect3.width + 2*padding, rect3.height + 2*padding)
        pygame.draw.rect(screen, (0,0,0), rect3_black)
        pygame.draw.rect(screen, col3, rect3)
        pygame.draw.rect(screen, (255,0,0), rect3, 2)
        ml_count = 0 if disable_mouse else mouse_left_count
        mouse_left_text_disp = small_font.render(str(ml_count), True, (255,255,255))
        text_rect3 = mouse_left_text_disp.get_rect(center=rect3.center)
        screen.blit(mouse_left_text_disp, text_rect3)
        col4 = get_highlight_color("mouse_right", current_time) if not disable_mouse else (200,200,200)
        rect4 = pygame.Rect(x_square, y_square_start + 3*(square_height + spacing), square_width, square_height)
        rect4_black = pygame.Rect(rect4.x - padding, rect4.y - padding, rect4.width + 2*padding, rect4.height + 2*padding)
        pygame.draw.rect(screen, (0,0,0), rect4_black)
        pygame.draw.rect(screen, col4, rect4)
        pygame.draw.rect(screen, (255,0,0), rect4, 2)
        mr_count = 0 if disable_mouse else mouse_right_count
        mouse_right_text_disp = small_font.render(str(mr_count), True, (255,255,255))
        text_rect4 = mouse_right_text_disp.get_rect(center=rect4.center)
        screen.blit(mouse_right_text_disp, text_rect4)
        draw_hit_error_bar(screen, hit_errors)
        if hp <= 0:
            game_over_text = font.render("GAME OVER", True, (255,0,0))
            game_over_rect = game_over_text.get_rect(center=(w//2, h//2))
            screen.blit(game_over_text, game_over_rect)
            pygame.display.flip()
            pygame.time.delay(2000)
            return
        pygame.display.flip()
        clock.tick(120)


def run_menu():
    global imported_map_filename
    menu = True
    pygame.mouse.set_visible(True)
    button_width = 300
    button_height = 75
    start_button = pygame.Rect(w//2 - button_width//2, h//2 - 150, button_width, button_height)
    settings_button = pygame.Rect(w//2 - button_width//2, h//2 - 50, button_width, button_height)
    quit_button = pygame.Rect(w//2 - button_width//2, h//2 + 50, button_width, button_height)
    map_maker_button = pygame.Rect(w//2 - button_width//2, h//2 + 150, button_width, button_height)
    export_button = pygame.Rect(w//2 - button_width//2, h - button_height - 20, button_width, button_height)

    while menu:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button in [4,5]:
                    continue
                mouse_x, mouse_y = event.pos
                if start_button.collidepoint(mouse_x, mouse_y):
                    menu = False
                elif settings_button.collidepoint(mouse_x, mouse_y):
                    run_settings()
                elif quit_button.collidepoint(mouse_x, mouse_y):
                    pygame.quit(); exit()
                elif map_maker_button.collidepoint(mouse_x, mouse_y):
                    run_map_maker()
                elif export_button.collidepoint(mouse_x, mouse_y):
                    import_map_file()
        screen.fill((0, 0, 0))
        title_text = title_font.render("Oku!Rwa", True, (255,255,255))
        title_rect = title_text.get_rect(center=(w//2, h//2 - 250))
        screen.blit(title_text, title_rect)
        pygame.draw.rect(screen, (100,100,100), start_button)
        pygame.draw.rect(screen, (255,0,0), start_button, 2)
        start_text = font.render("START", True, (255,255,255))
        screen.blit(start_text, start_text.get_rect(center=start_button.center))
        pygame.draw.rect(screen, (100,100,100), settings_button)
        pygame.draw.rect(screen, (255,0,0), settings_button, 2)
        settings_text = font.render("SETTINGS", True, (255,255,255))
        screen.blit(settings_text, settings_text.get_rect(center=settings_button.center))
        pygame.draw.rect(screen, (100,100,100), quit_button)
        pygame.draw.rect(screen, (255,0,0), quit_button, 2)
        quit_text = font.render("QUIT", True, (255,255,255))
        screen.blit(quit_text, quit_text.get_rect(center=quit_button.center))
        pygame.draw.rect(screen, (100,100,100), map_maker_button)
        pygame.draw.rect(screen, (255,0,0), map_maker_button, 2)
        map_text = font.render("MAP MAKER", True, (255,255,255))
        screen.blit(map_text, map_text.get_rect(center=map_maker_button.center))
        pygame.draw.rect(screen, (100,100,100), export_button)
        pygame.draw.rect(screen, (0,255,0), export_button, 2)
        export_text = font.render("Export Map", True, (255,255,255))
        screen.blit(export_text, export_text.get_rect(center=export_button.center))
        credit_text = font.render("Made by: GUGA Ver: 0.08", True, (255,255,255))
        screen.blit(credit_text, (10, h - 30))
        pygame.display.flip()
        clock.tick(60)

def main():
    while True:
        run_menu()
        result = run_map_picker()
        if result == "back":
            continue
        run_game()

main()
