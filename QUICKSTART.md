# WriteBot Quick Start Guide

Get up and running with WriteBot in 5 minutes!

## 🚀 Installation (2 minutes)

### 1. Clone and Enter Directory
```bash
git clone https://github.com/ariedotcodotnz/WriteBot.git
cd WriteBot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize Database
```bash
python init_db.py
```

When prompted:
- **Create admin user**: `yes`
- **Username**: Choose your admin username (e.g., `admin`)
- **Password**: Choose a secure password
- **Full name**: Your name (optional)
- **Create demo users**: `no` (unless you want test accounts)

### 4. Start the Application
```bash
python webapp/app.py
```

You should see:
```
* Running on http://127.0.0.1:5000
```

## 📝 First Generation (2 minutes)

### 1. Open the Web Interface
Open your browser and navigate to: `http://localhost:5000`

### 2. Log In
Use the admin credentials you created during setup.

### 3. Generate Your First Handwriting

**Enter some text:**
```
Hello, World!

This is my first handwritten text created with WriteBot.

It looks pretty realistic!
```

**Configure settings (or use defaults):**
- **Style**: 1 (or try 0-9 for different handwriting styles)
- **Bias**: 0.75 (lower = more random, higher = more consistent)
- **Stroke Color**: Black
- **Stroke Width**: 1

**Click "Generate Handwriting"**

### 4. View and Download
- Preview appears in the lightbox
- Click individual pages to view full size
- Click "Download All SVG Files" to save

**🎉 Congratulations!** You've generated your first handwritten document!

## 🎨 Try Different Styles (1 minute)

WriteBot includes 10 different handwriting styles (0-9). Try them out:

1. Change the **Style** number (0-9)
2. Click **Generate Handwriting** again
3. Compare the results

**Pro tip:** Style 1, 5, and 9 tend to be the most readable.

## 📦 Batch Processing

### Create a CSV File

Create `input.csv`:
```csv
name,text
letter1,"Dear Friend, How are you?"
letter2,"Thank you for your help."
letter3,"See you tomorrow!"
```

### Upload and Process

1. Go to the **Batch Processing** section
2. Click **Upload CSV** or drag-and-drop `input.csv`
3. Configure settings
4. Click **Generate Batch**
5. Download the ZIP file with all generated documents

## ⚙️ Common Settings Explained

| Setting | Description | Recommended Range |
|---------|-------------|-------------------|
| **Style** | Handwriting style (0-9) | 1, 5, or 9 for readability |
| **Bias** | Consistency vs randomness | 0.6-0.85 for natural look |
| **Stroke Color** | Ink color | Black, Blue, or custom |
| **Stroke Width** | Line thickness | 1-2 |
| **Page Size** | Paper size | A4 (default) |
| **Orientation** | Portrait or Landscape | Portrait |

## 🔧 Advanced Features

### Custom Page Templates

1. Go to **Admin** → **Templates**
2. Click **Create New Template**
3. Configure page size, margins, and style
4. Save and use in main interface

### Character Overrides

Customize individual characters:
1. **Admin** → **Character Overrides**
2. Create custom SVG for specific characters
3. Apply to your generations

### Page Size Presets

Create custom page sizes:
1. **Admin** → **Page Sizes**
2. Add custom dimensions
3. Use in templates or main interface

## 📚 Next Steps

Now that you're up and running:

- **[User Guide](docs/TEXT_PROCESSING_GUIDE.md)** - Learn advanced text processing
- **[API Documentation](docs/build/html/index.html)** - Use WriteBot programmatically
- **[Authentication Guide](docs/AUTHENTICATION.md)** - Manage users and security
- **[Full README](README.md)** - Complete documentation

## 🐛 Troubleshooting

### Application won't start
```bash
# Check Python version (needs 3.8+)
python --version

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Can't log in
```bash
# Reset database and create new admin user
rm writebot.db
python init_db.py
```

### Generated text looks wrong
- Check that your text only uses supported characters
- Try adjusting the bias parameter
- Try a different style number

### Port 5000 already in use
```bash
# Run on a different port
export FLASK_RUN_PORT=5001
python webapp/app.py
```

## 💡 Tips for Best Results

1. **Start with simple text** - Test with a short sentence first
2. **Use standard characters** - Stick to A-Z, a-z, 0-9, and basic punctuation
3. **Keep paragraphs short** - Empty lines work best for paragraph breaks
4. **Experiment with bias** - Try values between 0.5 and 0.95
5. **Compare styles** - Different styles suit different content
6. **Use templates** - Save time with page presets

## 🎯 Common Use Cases

### 1. Personal Letters
```python
# Use Style 1 or 5 for formal letters
# Bias: 0.75-0.85 for consistent appearance
# A4 Portrait with standard margins
```

### 2. Creative Writing
```python
# Use Style 9 for artistic look
# Bias: 0.6-0.7 for more variation
# Custom page size if needed
```

### 3. Practice Worksheets
```python
# Use Style 2 or 3
# Bias: 0.8-0.9 for uniform appearance
# Add margin lines and guides
```

## 📞 Getting Help

- **Documentation**: Check the [docs/](docs/) directory
- **Issues**: Search [GitHub Issues](https://github.com/ariedotcodotnz/WriteBot/issues)
- **Questions**: Start a discussion on GitHub

## ✅ Quick Reference

### Start Application
```bash
python webapp/app.py
```

### Access Web Interface
```
http://localhost:5000
```

### Default Admin Path
```
http://localhost:5000/admin
```

### API Endpoint
```
POST http://localhost:5000/api/v1/generate
```

### Database Migrations
```bash
cd webapp
python migrations/migrate.py status
python migrations/migrate.py up
```

### Backup Database
```bash
cd webapp
python migrations/db_utils.py backup
```

---

**You're all set!** Enjoy using WriteBot! 🎉

For more detailed information, see the [full README](README.md).
