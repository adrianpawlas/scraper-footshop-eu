# Footshop EU Product Scraper

A comprehensive scraper for Footshop EU that extracts product information, generates image embeddings using SigLIP, and stores data in Supabase.

## Features

- 🛍️ Scrapes all products from Footshop EU
- 🖼️ Downloads product images and generates **MANDATORY** 768-dimensional embeddings using Google SigLIP
- 🗄️ Stores data in Supabase with full product schema
- 🔄 Handles rate limiting and retries
- 📊 Progress tracking and error handling
- 🧪 Test suite for individual components

## Database Schema

The scraper populates a Supabase table with the following structure:

```sql
create table public.products (
  id text not null,
  source text null,
  product_url text null,
  affiliate_url text null,
  image_url text not null,
  brand text null,
  title text not null,
  description text null,
  category text null,
  gender text null,
  price double precision null,
  currency text null,
  search_tsv tsvector null,
  created_at timestamp with time zone null default now(),
  metadata text null,
  size text null,
  second_hand boolean null default false,
  embedding public.vector null,
  country text null,
  compressed_image_url text null,
  tags text[] null,
  search_vector tsvector null,
  constraint products_pkey primary key (id),
  constraint products_source_product_url_key unique (source, product_url)
) TABLESPACE pg_default;
```

## Setup

### Local Development

1. **Clone and install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```bash
   cp env.example .env
   ```

   Edit `.env` with your Supabase credentials:
   ```env
   SUPABASE_URL=your_supabase_url_here
   SUPABASE_KEY=your_supabase_anon_key_here
   ```

3. **Run tests to verify setup:**
   ```bash
   python test_scraper.py
   ```

### GitHub Actions Automation

The scraper runs automatically every day at midnight UTC and can also be triggered manually.

#### Setting up Secrets

1. Go to your repository settings: https://github.com/adrianpawlas/scraper-footshop-eu/settings/secrets/actions
2. Add the following secrets:
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_SERVICE_ROLE_KEY`: Your Supabase service_role key (bypasses RLS for full database access)

#### Manual Triggers

You can manually trigger the scraper from the Actions tab:

1. Go to the Actions tab in your repository
2. Select "Scrape Footshop EU Products" workflow
3. Click "Run workflow"
4. Configure options:
   - **Batch size**: Number of products to process concurrently (default: 10)
   - **Limit**: Maximum products to scrape (0 = unlimited, default: 0)
   - **Mode**: `full` for complete scraping, `test` for limited testing
   - **Test limit**: Limit for test mode (default: 50)

#### Automatic Schedule

- **Daily run**: Every day at midnight UTC (00:00)
- **Timeout**: 12 hours maximum per run
- **Artifacts**: Logs and run summaries are automatically saved

#### Troubleshooting

**403 Forbidden Errors:**
If you encounter 403 errors on the sitemap or product pages, this is likely due to IP blocking by Footshop. The scraper includes browser-like headers to minimize this, but if issues persist:

1. **Check logs**: Look for "Sitemap blocked (403)" messages
2. **Alternative approach**: May need to implement product URL discovery via Footshop's main pages instead of sitemap
3. **Rate limiting**: The scraper includes built-in delays to avoid triggering blocks

**SigLIP Model Issues:**
- Ensure all dependencies are installed: `sentencepiece`, `protobuf`, updated `transformers`
- Model loading requires ~2GB RAM and may be slow on CPU-only environments

## Usage

### Full Scraping
Scrape all products from Footshop EU:
```bash
python main.py --mode full --batch-size 10 --limit 100
```

### Single Product Testing
Test with a single product:
```bash
python main.py --mode single --url "https://www.footshop.eu/en/mens-shoes/397888-air-jordan-11-retro-gamma-blue-black-gamma-blue-black-varsity-maize.html"
```

### View Statistics
Check current scraping statistics:
```bash
python main.py --mode stats
```

## Configuration

Key settings in `config.py`:

- `CONCURRENT_REQUESTS`: Number of concurrent requests (default: 5)
- `RATE_LIMIT_DELAY`: Delay between requests in seconds (default: 1)
- `MAX_RETRIES`: Maximum retry attempts (default: 3)
- `IMAGE_SIZE`: Target image size for embedding (384x384)
- `EMBEDDING_DIM`: Expected embedding dimension (768)

## Architecture

The scraper consists of several components:

- **SitemapParser**: Extracts product URLs from Footshop's XML sitemap
- **ProductScraper**: Scrapes individual product pages and extracts JSON data
- **ImageProcessor**: Downloads images and generates SigLIP embeddings
- **DataMapper**: Transforms raw data to database schema
- **SupabaseClient**: Handles database operations
- **Main Orchestrator**: Coordinates the entire pipeline

## Error Handling

- Automatic retries with exponential backoff
- Rate limiting to prevent server overload
- Comprehensive logging to `scraper.log`
- Graceful handling of missing data
- Data validation before database insertion

## Requirements

- Python 3.8+
- CUDA-compatible GPU (recommended for embedding generation)
- **CRITICAL**: SigLIP model `google/siglip-base-patch16-384` **MUST** load successfully
- Supabase account with vector extension enabled
- Sufficient disk space for image processing

## Notes

- The scraper respects Footshop's robots.txt
- **MANDATORY**: Image embeddings use `google/siglip-base-patch16-384` model only (no fallbacks)
- Products are uniquely identified by `(source, product_url)` combination
- The scraper can resume interrupted runs (products are upserted)

## Troubleshooting

1. **CUDA out of memory**: Reduce batch size or use CPU-only mode
2. **Rate limiting**: Increase `RATE_LIMIT_DELAY` in config
3. **Database connection issues**: Verify Supabase credentials
4. **SigLIP loading failure**: Check transformers version (>=4.44.0) and internet connection
5. **Embeddings are MANDATORY**: Scraper **FAILS** if SigLIP cannot generate embeddings (no fallbacks)

## Contributing

1. Run tests: `python test_scraper.py`
2. Check logs: `tail -f scraper.log`
3. Add new features with proper error handling
4. Update documentation for configuration changes
