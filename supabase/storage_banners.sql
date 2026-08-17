-- Bucket público para banners enviados pelo admin (site estático)
-- Execute no Supabase SQL Editor após browser_api.sql

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'banners',
  'banners',
  true,
  5242880,
  ARRAY['image/jpeg', 'image/jpg', 'image/png']
)
ON CONFLICT (id) DO UPDATE SET
  public = EXCLUDED.public,
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;

DROP POLICY IF EXISTS "Public read banners" ON storage.objects;
CREATE POLICY "Public read banners" ON storage.objects
  FOR SELECT TO public
  USING (bucket_id = 'banners');

DROP POLICY IF EXISTS "Admin insert banners" ON storage.objects;
CREATE POLICY "Admin insert banners" ON storage.objects
  FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'banners');

DROP POLICY IF EXISTS "Admin update banners" ON storage.objects;
CREATE POLICY "Admin update banners" ON storage.objects
  FOR UPDATE TO authenticated
  USING (bucket_id = 'banners');

DROP POLICY IF EXISTS "Admin delete banners" ON storage.objects;
CREATE POLICY "Admin delete banners" ON storage.objects
  FOR DELETE TO authenticated
  USING (bucket_id = 'banners');
