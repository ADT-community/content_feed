/* content_feed demo data. All creators are fictional; videos are generated placeholders. */
window.FEED_DATA = {
  creators: {
    amaka:   { handle: "amaka.moves",    name: "Amaka Obi",      city: "Lagos, Nigeria",   color: "#e8a33d", followers: 48200, bio: "Dancer · teaching Afrobeats choreo every week" },
    kofi:    { handle: "chef_kofi",      name: "Kofi Mensah",    city: "Accra, Ghana",     color: "#d4603a", followers: 31700, bio: "Home cook. Ghana jollof is the best jollof." },
    wanjiku: { handle: "wanjiku_laughs", name: "Wanjiku Kamau",  city: "Nairobi, Kenya",   color: "#b06ad4", followers: 92500, bio: "Comedy skits about office life" },
    tunde:   { handle: "tunde_explores", name: "Tunde Alabi",    city: "Lagos, Nigeria",   color: "#2b6cb0", followers: 15800, bio: "Markets, street food and hidden spots" },
    zainab:  { handle: "zainab.codes",   name: "Zainab Yusuf",   city: "Kano, Nigeria",    color: "#5fae7a", followers: 22300, bio: "Software engineer. Short coding lessons." },
    juma:    { handle: "farmer_juma",    name: "Juma Mwangi",    city: "Nakuru, Kenya",    color: "#7aa83a", followers: 9400,  bio: "Smallholder farmer sharing what works" }
  },
  posts: [
    { id: "p1", creator: "amaka",   video: "media/dance.mp4",  caption: "Learning the new choreo, slow version first 🔥 #afrobeats #dance", sound: "Original sound · amaka.moves", likes: 12400, comments: [["temi_b", "Teach us the second part!"], ["kwame.d", "The footwork 😮"]], tips: 412 },
    { id: "p2", creator: "kofi",    video: "media/jollof.mp4", caption: "Ghana jollof in 60 seconds. Fight me 😄 #jollof #cooking", sound: "Kitchen beats · chef_kofi", likes: 8900, comments: [["naija_foodie", "Nigerian jollof clears 😂"], ["ama.k", "Saving this for Sunday"]], tips: 233 },
    { id: "p3", creator: "wanjiku", video: "media/skit.mp4",   caption: "When the boss says 'quick meeting' (part 3) #comedy #officelife", sound: "Original sound · wanjiku_laughs", likes: 40100, comments: [["otieno", "Part 4 when??"], ["fatou.s", "This is my office 😭"], ["brian_ke", "The face at the end"]], tips: 1290 },
    { id: "p4", creator: "tunde",   video: "media/market.mp4", caption: "Balogun market tour: where to find the best fabric prices #lagos", sound: "Market noise · tunde_explores", likes: 3100, comments: [["shopwithbisi", "Which line is this?"]], tips: 97 },
    { id: "p5", creator: "zainab",  video: "media/code.mp4",   caption: "3 tips to make your app work on cheap phones 📱 #coding #tech", sound: "Lo-fi study · zainab.codes", likes: 6700, comments: [["dev_musa", "Tip 2 saved my app"], ["lindiwe.dev", "More of these please"]], tips: 356 },
    { id: "p6", creator: "juma",    video: "media/farm.mp4",   caption: "Harvest day! What I changed this season to double my maize #farming", sound: "Morning birds · farmer_juma", likes: 2200, comments: [["mama_shamba", "What fertiliser?"]], tips: 61 }
  ],
  gifts: [
    { id: "baobab", emoji: "🌳", name: "Baobab",       amount: 200 },
    { id: "drum",   emoji: "🥁", name: "Talking drum", amount: 500 },
    { id: "lion",   emoji: "🦁", name: "Lion",         amount: 1000 },
    { id: "crown",  emoji: "👑", name: "Crown",        amount: 5000 }
  ],
  me: {
    handle: "you", name: "You", balance: 18400,
    supporters: [["temi_b", 2000, "🦁"], ["kwame.d", 500, "🥁"], ["ama.k", 1000, "tip"], ["otieno", 200, "🌳"]]
  }
};
