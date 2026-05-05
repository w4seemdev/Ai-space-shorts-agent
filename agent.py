
from groq import Groq
from dotenv import load_dotenv
import os
import json
import asyncio
import edge_tts
import subprocess
import random
load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
import random

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
        "The universe is completely flat not curved",
        "Stars that explode twice hypernovas",
        "The coldest place in the universe is man-made",
        "Io has volcanoes erupting sulfur 300 miles high",
        "Mercury shrinks a little more every year",
        "The Sun will become a red giant and swallow Earth",
        "There are zombie stars that refuse to die",
        "The universe has a sound a deep B-flat hum",
        "Saturn would float on water because it is less dense",
        "A year on Mercury is shorter than its day"
        # MIND-BENDING PHYSICS
        "What existed before the Big Bang",
        "The universe is made of mostly nothing — 99.9% empty space",
        "Light is both a wave and a particle at the same time",
        "Nothing can escape a black hole not even light",
        "The speed of light is the ultimate speed limit in the universe",
        "Time travel is theoretically possible near black holes",
        "The universe has no center and no edge",
        "Every atom in your body was made inside a star",
        "The Heisenberg uncertainty principle — you can never know everything",
        "Schrodingers cat and quantum superposition explained",
        
        # EXTREME SPACE OBJECTS
        "The largest black hole is 40 billion times the mass of our Sun",
        "Pulsars are the most accurate clocks in the universe",
        "Blazars shoot jets of energy directly at Earth",
        "Cosmic strings leftover from the Big Bang may still exist",
        "Strange stars made entirely of quarks may exist",
        "Theia the planet that crashed into Earth to form the Moon",
        "The Pillars of Creation where new stars are born right now",
        "Cygnus X-1 the first black hole ever discovered",
        "Sagittarius A the supermassive black hole in our galaxy",
        "The biggest explosion ever recorded — AT2021lwx quasar",
        
        # WEIRD SPACE FACTS
        "In space your body grows 2 inches taller",
        "Astronauts cry differently in space — tears dont fall",
        "A full NASA spacesuit costs 12 million dollars",
        "The Moon is moving away from Earth 1.5 inches per year",
        "One day on Jupiter is only 10 hours long",
        "The Sun is so big one million Earths could fit inside",
        "Olympus Mons on Mars is 3 times taller than Mount Everest",
        "The Great Wall of China cannot actually be seen from space",
        "Venus spins backwards compared to most planets",
        "The rings of Saturn will disappear in 100 million years",
        
        # SPACE DANGERS
        "Solar flares that could knock out all electricity on Earth",
        "Asteroid 99942 Apophis passing dangerously close in 2029",
        "Cosmic rays hitting Earth from distant exploding stars",
        "Rogue planets floating in darkness with no star",
        "Magnetar explosions that could sterilize planets from light years away",
        "The eventual death of our Sun in 5 billion years",
        "Supervolcanoes on Io that dwarf anything on Earth",
        "Space debris — 27000 pieces of junk orbiting Earth right now",
        "Coronal mass ejections that could end modern civilization",
        "The asteroid that killed the dinosaurs and what it left behind",
        
        # SPACE EXPLORATION HISTORY
        "Yuri Gagarin the first human in space in 1961",
        "The Space Race between USA and USSR during the Cold War",
        "The Challenger disaster that changed NASA forever",
        "The first spacewalk in 1965 by Alexei Leonov",
        "How astronauts sleep eat and go to the bathroom in space",
        "The longest time spent in space 437 days by Valeri Polyakov",
        "The first woman in space Valentina Tereshkova in 1963",
        "NASAs Artemis program bringing humans back to the Moon",
        "The secret military space plane X-37B orbiting Earth for years",
        "How rocket engines work and why they need no air in space",
        
        # FUTURE OF SPACE
        "Terraforming Mars to make it habitable for humans",
        "Space elevators that could replace rockets entirely",
        "Mining asteroids for gold platinum and rare minerals",
        "Dyson spheres built around stars to harvest all their energy",
        "Generation ships that travel for thousands of years to new stars",
        "The first humans who will be born on another planet",
        "Interstellar travel and what it would actually take",
        "Space tourism and the race to send civilians to orbit",
        "Colonizing the Moon as a stepping stone to Mars",
        "Printing organs and food in space using 3D printers",
        
        # ALIEN SCIENCE
        "The Kardashev scale — measuring alien civilizations",
        "Fast Radio Bursts — mysterious signals from across the universe",
        "Oumuamua the mysterious interstellar object that visited our solar system",
        "Pentagon UFO reports officially released by the US government",
        "The Zoo hypothesis — maybe aliens are watching but not contacting",
        "SETI — 60 years of listening for alien signals",
        "The possibility of life in Jupiters atmosphere",
        "Titan could support life unlike anything we know",
        "Enceladus shooting water geysers into space from its ocean",
        "The search for biosignatures on exoplanet atmospheres",
        
        # AMAZING COMPARISONS
        "If the Sun were a door the Earth would be a coin",
        "The nearest star is so far light takes 4 years to reach us",
        "The Milky Way has 400 billion stars — more than humans who ever lived",
        "The universe is 13.8 billion years old — Earth is only 4.5 billion",
        "If Earth history were a calendar humans appeared in the last 10 seconds",
        "The observable universe is 93 billion light years across",
        "There are more galaxies than every grain of sand on every beach",
        "Traveling at light speed it would take 2 million years to reach Andromeda",
        "The deepest we have ever looked into space saw galaxies from 400 million years after the Big Bang",
        "Sound in space would travel so slowly it would take 18 years to cross our solar system"
    ]
    
    # Python picks the topic randomly — not the AI!
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
def generate_voiceover(script):
    print("🎙️ Generating voiceover...")
    full_text = f"{script['hook']} {script['facts']} {script['cta']}"

    async def create_audio():
        communicate = edge_tts.Communicate(full_text, voice="en-US-GuyNeural")
        await communicate.save("voiceover.mp3")

    asyncio.run(create_audio())
    print("✅ Voiceover saved!")

def build_video(script):
    print("🎬 Building video with text overlay...")

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
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-t", "60",
        "-i", "background.mp4",
        "-i", "voiceover.mp3",
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
        "output.mp4"
    ]

    subprocess.run(command, check=True)
    print("✅ Video saved as output.mp4!")

# Run the full pipeline
script = generate_script()
print(f"\n📹 Title: {script['title']}\n")
generate_voiceover(script)
build_video(script)
print("\n🚀 Done! Open output.mp4 to watch your Short!")


import schedule
import time
from upload import upload_video

def run_agent():
    print("\n⏰ Agent started — creating new Short...")
    script = generate_script()
    print(f"\n📹 Title: {script['title']}\n")
    generate_voiceover(script)
    build_video(script)
    upload_video(script['title'])
    print("\n✅ Short created and uploaded successfully!")

# Run once immediately
run_agent()

# Then schedule every day at 9:00 AM
schedule.every().day.at("09:00").do(run_agent)

print("\n🤖 Agent is running! Will post every day at 9:00 AM")
print("Press Ctrl+C to stop\n")

while True:
    schedule.run_pending()
    time.sleep(60)