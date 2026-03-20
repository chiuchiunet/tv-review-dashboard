# F1 Live Dashboard

🏎️ Interactive F1 Dashboard displaying live race data from the OpenF1 API.

## Features

- **Live Positions** - Real-time driver positions with team colors and gap to leader
- **Lap Times** - Latest lap times with sector splits (highlights fastest lap)
- **Pit Stops** - Pit stop history with duration and stop numbers
- **Driver Comparison** - Compare lap times between any two drivers
- **Constructor Standings** - Team points based on current race positions

## Data Source

Uses the free [OpenF1 API](https://openf1.org/) for live F1 data:
- Live positions and intervals
- Lap times with sector data
- Pit stop information
- Driver and team information

## Deployment to Vercel

### Option 1: Vercel CLI (Recommended)

1. Install Vercel CLI:
```bash
npm i -g vercel
```

2. Login to Vercel:
```bash
vercel login
```

3. Deploy:
```bash
cd f1-dashboard
vercel
```

Follow the prompts:
- Set up and deploy? **Yes**
- Which scope? **Your GitHub username**
- Want to modify settings? **No**
- Project name: **f1-dashboard** (or your preferred name)

4. Your dashboard will be live at: `https://your-project.vercel.app`

### Option 2: GitHub + Vercel

1. Create a new repository on GitHub:
   - Go to https://github.com/new
   - Repository name: `f1-dashboard`
   - Make it **Public**
   - Click "Create repository"

2. Push your code:
```bash
cd f1-dashboard
git init
git add .
git commit -m "Initial F1 Dashboard"
git remote add origin https://github.com/YOUR_USERNAME/f1-dashboard.git
git push -u origin main
```

3. Deploy on Vercel:
   - Go to https://vercel.com
   - Click "Add New..." → "Project"
   - Import your GitHub repository
   - Click "Deploy"

That's it! 🎉

## Local Development

Simply open `index.html` in a browser, or use a local server:

```bash
# Python
python -m http.server 8000

# Node
npx serve .
```

Then open http://localhost:8000

## Notes

- The dashboard auto-refreshes every 5 seconds
- Data is only available during race sessions
- Constructor standings are simulated based on current race positions (OpenF1 doesn't provide championship data)
- Works on desktop and mobile devices

## Tech Stack

- Pure HTML/CSS/JavaScript (no frameworks)
- OpenF1 API
- Vercel for hosting (free)
