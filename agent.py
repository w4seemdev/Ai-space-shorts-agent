
# from groq import Groq
# from dotenv import load_dotenv
# import os
# import json
# import asyncio
# import edge_tts
# import subprocess
# import random

# load_dotenv()

# groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# def generate_script():
#     print("🤖 Generating script...")
#     random_seed = os.urandom(8).hex()

#     topics = [
#         "Black holes and what happens if you fall in",
#         "Neutron stars spinning 700 times per second",
#         "White dwarfs slowly cooling for trillions of years",
#         "Magnetars with the strongest magnetic fields in the universe",
#         "Red giants swallowing their planets",
#         "Supernovas brighter than entire galaxies",
#         "Gamma ray bursts the most powerful explosions ever",
#         "Binary star systems orbiting each other",
#         "Rogue stars ejected from galaxies at millions of mph",
#         "Venus hotter than Mercury despite being farther from the Sun",
#         "Jupiters Great Red Spot storm bigger than Earth",
#         "Saturns rings made of billions of ice chunks",
#         "Titan Saturns moon with lakes of liquid methane",
#         "Europas ocean hidden under miles of ice",
#         "Uranus rotates on its side",
#         "Neptunes wind speeds of 1500 mph",
#         "Plutos heart-shaped nitrogen glacier",
#         "The Milky Way is on a collision course with Andromeda",
#         "Supermassive black holes at the center of every galaxy",
#         "The Great Attractor pulling everything including us",
#         "Quasars brighter than a trillion suns",
#         "Dark matter making up 27 percent of the universe",
#         "Dark energy causing the universe to expand faster",
#         "Time slows down near massive objects time dilation",
#         "Wormholes shortcuts through space-time",
#         "The universe might be inside a black hole",
#         "Parallel universes in the multiverse theory",
#         "Hawking radiation black holes slowly evaporate",
#         "Spaghettification what happens near a black hole",
#         "The Big Bang came from a single point smaller than an atom",
#         "Quantum entanglement connecting particles across the universe",
#         "The Voyager probe leaving our solar system after 46 years",
#         "The James Webb telescope seeing the first galaxies ever formed",
#         "Apollo 11 moon landing and what they left behind",
#         "The ISS traveling at 17500 mph orbiting Earth 16 times daily",
#         "SpaceX Starship the biggest rocket ever built",
#         "The Mars rovers discovering ancient riverbeds",
#         "Hubbles Deep Field photo 10000 galaxies in one image",
#         "Plans to build a base on the Moon by 2030",
#         "The Drake equation estimating alien civilizations",
#         "The Fermi paradox where is everyone",
#         "The Wow signal unexplained radio burst from space",
#         "TRAPPIST-1 system with 7 Earth-sized planets",
#         "Panspermia life spreading through asteroids",
#         "A day on Venus is longer than a year on Venus",
#         "The footprints on the Moon will last millions of years",
#         "The Sun loses 4 million tons of mass every second",
#         "There are more stars than grains of sand on Earth",
#         "A teaspoon of neutron star weighs a billion tons",
#         "Space smells like seared steak and hot metal",
#         "What existed before the Big Bang",
#         "Every atom in your body was made inside a star",
#         "The largest black hole is 40 billion times the mass of our Sun",
#         "Pulsars are the most accurate clocks in the universe",
#         "The Pillars of Creation where new stars are born right now",
#         "Sagittarius A the supermassive black hole in our galaxy",
#         "In space your body grows 2 inches taller",
#         "The Moon is moving away from Earth 1.5 inches per year",
#         "One day on Jupiter is only 10 hours long",
#         "Olympus Mons on Mars is 3 times taller than Mount Everest",
#         "Venus spins backwards compared to most planets",
#         "The rings of Saturn will disappear in 100 million years",
#         "Solar flares that could knock out all electricity on Earth",
#         "Space debris 27000 pieces of junk orbiting Earth right now",
#         "The asteroid that killed the dinosaurs and what it left behind",
#         "Yuri Gagarin the first human in space in 1961",
#         "How astronauts sleep eat and go to the bathroom in space",
#         "Terraforming Mars to make it habitable for humans",
#         "Mining asteroids for gold platinum and rare minerals",
#         "Dyson spheres built around stars to harvest all their energy",
#         "Fast Radio Bursts mysterious signals from across the universe",
#         "Oumuamua the mysterious interstellar object that visited our solar system",
#         "Enceladus shooting water geysers into space from its ocean",
#         "If the Sun were a door the Earth would be a coin",
#         "The nearest star is so far light takes 4 years to reach us",
#         "Saturn would float on water because it is less dense",
#         "A year on Mercury is shorter than its day",
#         "Stars older than the universe itself",
#         "Io the most volcanically active world in the solar system",
#         "Mercury shrinks a little more every year",
#         "There are zombie stars that refuse to die",
#         "Titan could support life unlike anything we know",
#         "The search for biosignatures on exoplanet atmospheres"
#     ]

#     chosen_topic = random.choice(topics)
#     print(f"📌 Topic chosen: {chosen_topic}")

#     response = groq_client.chat.completions.create(
#         model="llama-3.3-70b-versatile",
#         messages=[
#             {
#                 "role": "system",
#                 "content": """You are a YouTube Shorts script writer specializing in space and science facts.
#                 Always respond in this exact JSON format with no extra text:
#                 {
#                     "title": "video title here",
#                     "hook": "first 2 sentences to grab attention",
#                     "facts": "3-4 interesting facts about the topic",
#                     "cta": "call to action (follow for more space facts!)"
#                 }"""
#             },
#             {
#                 "role": "user",
#                 "content": f"Write a YouTube Shorts script specifically about: {chosen_topic}. Make it exciting and mind-blowing!"
#             }
#         ]
#     )
#     return json.loads(response.choices[0].message.content)

# def generate_voiceover(script):
#     print("🎙️ Generating voiceover...")
#     full_text = f"{script['hook']} {script['facts']} {script['cta']}"

#     async def create_audio():
#         communicate = edge_tts.Communicate(full_text, voice="en-US-GuyNeural")
#         await communicate.save("voiceover.mp3")

#     asyncio.run(create_audio())
#     print("✅ Voiceover saved!")

# def build_video(script):
#     print("🎬 Building video with text overlay...")

#     # Pick random background
#     backgrounds = ["bg1.mp4", "bg2.mp4", "bg3.mp4", "bg4.mp4", "bg5.mp4"]
#     available = [b for b in backgrounds if os.path.exists(b)]
#     if not available:
#         available = ["background.mp4"]
#     background = random.choice(available)
#     print(f"🎥 Using background: {background}")

#     full_text = f"{script['hook']} {script['facts']}"
#     words = full_text.split()
#     lines = []
#     current = []
#     for word in words:
#         current.append(word)
#         if len(current) >= 6:
#             lines.append(" ".join(current))
#             current = []
#     if current:
#         lines.append(" ".join(current))

#     display_text = "\n".join(lines[:4])
#     display_text = display_text.replace("'", "").replace(":", "").replace(",", "")

#     command = [
#         ".\\ffmpeg.exe", "-y",
#         "-stream_loop", "-1",
#         "-t", "60",
#         "-i", background,
#         "-i", "voiceover.mp3",
#         "-map", "0:v:0",
#         "-map", "1:a:0",
#         "-vf", (
#             "scale=1080:1920:force_original_aspect_ratio=increase,"
#             "crop=1080:1920,setsar=1,"
#             f"drawtext=text='{display_text}':"
#             "fontsize=50:fontcolor=white:"
#             "x=(w-text_w)/2:y=h-th-100:"
#             "box=1:boxcolor=black@0.5:boxborderw=10:"
#             "font=Arial:line_spacing=10"
#         ),
#         "-c:v", "libx264",
#         "-c:a", "aac",
#         "-shortest",
#         "-preset", "ultrafast",
#         "-crf", "28",
#         "-threads", "0",
#         "output.mp4"
#     ]

#     subprocess.run(command, check=True)
#     print("✅ Video saved as output.mp4!")

# # Run the full pipeline
# script = generate_script()
# print(f"\n📹 Title: {script['title']}\n")
# generate_voiceover(script)
# build_video(script)
# print("\n🚀 Video created!")

# # Auto upload to YouTube
# from upload import upload_video
# upload_video(script['title'] + " #shorts #space #science")
# print("\n✅ Uploaded to YouTube automatically!")

from groq import Groq
from dotenv import load_dotenv
import os
import json
import asyncio
import edge_tts
import subprocess
import random
from datetime import datetime
from upload import upload_video

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_script():
    print("🤖 Generating script...")

    topics = [
        "Black holes and what happens if you fall in",
        "Neutron stars spinning 700 times per second",
        "White dwarfs slowly cooling for trillions of years",
        "Magnetars with the strongest magnetic fields in the universe",
        "Red giants swallowing their planets",
        "Supernovas brighter than entire galaxies",
        "Gamma ray bursts the most powerful explosions ever",
        "Binary star systems orbiting each other",
        "Rogue stars ejected from galaxies at millions of mph",
        "Venus hotter than Mercury despite being farther from the Sun",
        "Jupiters Great Red Spot storm bigger than Earth",
        "Saturns rings made of billions of ice chunks",
        "Titan Saturns moon with lakes of liquid methane",
        "Europas ocean hidden under miles of ice",
        "Uranus rotates on its side",
        "Neptunes wind speeds of 1500 mph",
        "Plutos heart-shaped nitrogen glacier",
        "The Milky Way is on a collision course with Andromeda",
        "Supermassive black holes at the center of every galaxy",
        "The Great Attractor pulling everything including us",
        "Quasars brighter than a trillion suns",
        "Dark matter making up 27 percent of the universe",
        "Dark energy causing the universe to expand faster",
        "Time slows down near massive objects time dilation",
        "Wormholes shortcuts through space-time",
        "The universe might be inside a black hole",
        "Parallel universes in the multiverse theory",
        "Hawking radiation black holes slowly evaporate",
        "Spaghettification what happens near a black hole",
        "The Big Bang came from a single point smaller than an atom",
        "Quantum entanglement connecting particles across the universe",
        "The Voyager probe leaving our solar system after 46 years",
        "The James Webb telescope seeing the first galaxies ever formed",
        "Apollo 11 moon landing and what they left behind",
        "The ISS traveling at 17500 mph orbiting Earth 16 times daily",
        "SpaceX Starship the biggest rocket ever built",
        "The Mars rovers discovering ancient riverbeds",
        "Hubbles Deep Field photo 10000 galaxies in one image",
        "Plans to build a base on the Moon by 2030",
        "The Drake equation estimating alien civilizations",
        "The Fermi paradox where is everyone",
        "The Wow signal unexplained radio burst from space",
        "TRAPPIST-1 system with 7 Earth-sized planets",
        "Panspermia life spreading through asteroids",
        "A day on Venus is longer than a year on Venus",
        "The footprints on the Moon will last millions of years",
        "The Sun loses 4 million tons of mass every second",
        "There are more stars than grains of sand on Earth",
        "A teaspoon of neutron star weighs a billion tons",
        "Space smells like seared steak and hot metal",
        "What existed before the Big Bang",
        "Every atom in your body was made inside a star",
        "The largest black hole is 40 billion times the mass of our Sun",
        "Pulsars are the most accurate clocks in the universe",
        "The Pillars of Creation where new stars are born right now",
        "Sagittarius A the supermassive black hole in our galaxy",
        "In space your body grows 2 inches taller",
        "The Moon is moving away from Earth 1.5 inches per year",
        "One day on Jupiter is only 10 hours long",
        "Olympus Mons on Mars is 3 times taller than Mount Everest",
        "Venus spins backwards compared to most planets",
        "The rings of Saturn will disappear in 100 million years",
        "Solar flares that could knock out all electricity on Earth",
        "Space debris 27000 pieces of junk orbiting Earth right now",
        "The asteroid that killed the dinosaurs and what it left behind",
        "Yuri Gagarin the first human in space in 1961",
        "How astronauts sleep eat and go to the bathroom in space",
        "Terraforming Mars to make it habitable for humans",
        "Mining asteroids for gold platinum and rare minerals",
        "Dyson spheres built around stars to harvest all their energy",
        "Fast Radio Bursts mysterious signals from across the universe",
        "Oumuamua the mysterious interstellar object that visited our solar system",
        "Enceladus shooting water geysers into space from its ocean",
        "If the Sun were a door the Earth would be a coin",
        "The nearest star is so far light takes 4 years to reach us",
        "Saturn would float on water because it is less dense",
        "A year on Mercury is shorter than its day",
        "Stars older than the universe itself",
        "Io the most volcanically active world in the solar system",
        "Mercury shrinks a little more every year",
        "There are zombie stars that refuse to die",
        "Titan could support life unlike anything we know",
        "The search for biosignatures on exoplanet atmospheres"
    ]

    chosen_topic = random.choice(topics)
    print(f"📌 Topic chosen: {chosen_topic}")

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": """You are a YouTube Shorts script writer specializing in space and science facts.
                Always respond in this exact JSON format with no extra text:
                {
                    "title": "video title here",
                    "hook": "first 2 sentences to grab attention",
                    "facts": "3-4 interesting facts about the topic",
                    "cta": "call to action (follow for more space facts!)"
                }"""
            },
            {
                "role": "user",
                "content": f"Write a YouTube Shorts script specifically about: {chosen_topic}. Make it exciting and mind-blowing!"
            }
        ]
    )
    return json.loads(response.choices[0].message.content)

def generate_voiceover(script, filename):
    print("🎙️ Generating voiceover...")
    full_text = f"{script['hook']} {script['facts']} {script['cta']}"

    async def create_audio():
        communicate = edge_tts.Communicate(full_text, voice="en-US-GuyNeural")
        await communicate.save(filename)

    asyncio.run(create_audio())
    print("✅ Voiceover saved!")

def build_video(script, audio_file, output_file):
    print("🎬 Building video with text overlay...")

    backgrounds = ["bg1.mp4", "bg2.mp4", "bg3.mp4", "bg4.mp4", "bg5.mp4", "background.mp4"]
    available = [b for b in backgrounds if os.path.exists(b)]
    background = random.choice(available)
    print(f"🎥 Using background: {background}")

    full_text = f"{script['hook']} {script['facts']}"
    words = full_text.split()
    lines = []
    current = []
    for word in words:
        current.append(word)
        if len(current) >= 6:
            lines.append(" ".join(current))
            current = []
    if current:
        lines.append(" ".join(current))

    display_text = "\n".join(lines[:4])
    display_text = display_text.replace("'", "").replace(":", "").replace(",", "")

    command = [
        ".\\ffmpeg.exe", "-y",
        "-stream_loop", "-1",
        "-t", "60",
        "-i", background,
        "-i", audio_file,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-vf", (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,setsar=1,"
            f"drawtext=text='{display_text}':"
            "fontsize=50:fontcolor=white:"
            "x=(w-text_w)/2:y=h-th-100:"
            "box=1:boxcolor=black@0.5:boxborderw=10:"
            "font=Arial:line_spacing=10"
        ),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        "-preset", "ultrafast",
        "-crf", "28",
        "-threads", "0",
        output_file
    ]

    subprocess.run(command, check=True)
    print(f"✅ Video saved as {output_file}!")

# ▶️ Run the full pipeline
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
audio_file = f"voiceover_{timestamp}.mp3"
video_file = f"output_{timestamp}.mp4"

script = generate_script()
print(f"\n📹 Title: {script['title']}\n")
generate_voiceover(script, audio_file)
build_video(script, audio_file, video_file)

print("\n📤 Uploading to YouTube...")
upload_video(script['title'] + " #shorts #space #science")

print("\n✅ Done! New unique Short uploaded to YouTube!")
print(f"📁 Saved locally as: {video_file}")