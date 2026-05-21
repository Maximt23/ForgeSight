/*
 * Shared Coordinate Transformation Core (C#)
 * 
 * This module provides the core coordinate transformation logic used by
 * VIVE XR (VR -> SiteOwl). Matches the Python implementation exactly.
 * 
 * No external dependencies - pure C# math only.
 * 
 * Usage:
 *     var bounds = new Bounds(0, 0, 1000, 500);
 *     var transformer = new CoordinateTransformer(ScaleMode.FitContain);
 *     transformer.SetBounds(bounds);
 *     
 *     var result = transformer.Transform(500, 250);
 *     Debug.Log($"SiteOwl: ({result.SiteX}, {result.SiteY})");
 */

using System;
using System.Collections.Generic;

namespace CadOwl.Shared.Transform
{
    /// <summary>How to scale the content within the artboard.</summary>
    public enum ScaleMode
    {
        FitWidth,    // Scale to match width, center vertically
        FitHeight,   // Scale to match height, center horizontally
        FitContain,  // Fit within bounds without cropping (DEFAULT)
        FitCover,    // Fill bounds, may crop edges
        Stretch      // Stretch to fill (distorts aspect ratio)
    }

    /// <summary>Axis-aligned bounding box.</summary>
    public class Bounds
    {
        public float MinX { get; set; }
        public float MinY { get; set; }
        public float MaxX { get; set; }
        public float MaxY { get; set; }

        public Bounds() { }

        public Bounds(float minX, float minY, float maxX, float maxY)
        {
            MinX = minX;
            MinY = minY;
            MaxX = maxX;
            MaxY = maxY;
        }

        public float Width => MaxX - MinX;
        public float Height => MaxY - MinY;
        public (float x, float y) Center => ((MinX + MaxX) / 2, (MinY + MaxY) / 2);
        public float AspectRatio => Height != 0 ? Width / Height : 1.0f;

        /// <summary>Create bounding box from list of points.</summary>
        public static Bounds FromPoints(List<(float x, float y)> points)
        {
            if (points == null || points.Count == 0)
                return null;

            float minX = float.MaxValue, minY = float.MaxValue;
            float maxX = float.MinValue, maxY = float.MinValue;

            foreach (var (x, y) in points)
            {
                if (x < minX) minX = x;
                if (x > maxX) maxX = x;
                if (y < minY) minY = y;
                if (y > maxY) maxY = y;
            }

            return new Bounds(minX, minY, maxX, maxY);
        }

        /// <summary>Create from dictionary (JSON deserialization).</summary>
        public static Bounds FromDict(Dictionary<string, float> d)
        {
            return new Bounds(d["min_x"], d["min_y"], d["max_x"], d["max_y"]);
        }

        /// <summary>Convert to dictionary.</summary>
        public Dictionary<string, float> ToDict()
        {
            return new Dictionary<string, float>
            {
                {"min_x", MinX},
                {"min_y", MinY},
                {"max_x", MaxX},
                {"max_y", MaxY}
            };
        }
    }

    /// <summary>Result of coordinate transformation.</summary>
    public class TransformResult
    {
        public float ArtX { get; set; }       // Artboard X (0-1000)
        public float ArtY { get; set; }       // Artboard Y (0-1000)
        public float SiteX { get; set; }      // SiteOwl X (0-100)
        public float SiteY { get; set; }      // SiteOwl Y (0-100)
        public bool InBounds { get; set; }    // Within artboard bounds
        public float Confidence { get; set; } // Confidence (0-1)

        public Dictionary<string, object> ToDict()
        {
            return new Dictionary<string, object>
            {
                {"art_x", ArtX},
                {"art_y", ArtY},
                {"site_x", SiteX},
                {"site_y", SiteY},
                {"in_bounds", InBounds},
                {"confidence", Confidence}
            };
        }
    }

    /// <summary>
    /// Transform coordinates from source system to SiteOwl.
    /// Matches Python implementation exactly.
    /// </summary>
    public class CoordinateTransformer
    {
        public const int DefaultArtboardSize = 1000;
        public const int DefaultFloorplanSize = 800;

        public ScaleMode Mode { get; }
        public int ArtboardSize { get; }
        public int FloorplanSize { get; }
        public bool FlipY { get; }
        public float RotationRad { get; }

        private Bounds _bounds;
        private float _scaleX = 1.0f;
        private float _scaleY = 1.0f;
        private float _offsetX = 0.0f;
        private float _offsetY = 0.0f;

        public float Margin => (ArtboardSize - FloorplanSize) / 2.0f;
        public bool IsReady => _bounds != null;

        public CoordinateTransformer(
            ScaleMode mode = ScaleMode.FitContain,
            int artboardSize = DefaultArtboardSize,
            int floorplanSize = DefaultFloorplanSize,
            bool flipY = true,
            float rotationDeg = 0.0f)
        {
            Mode = mode;
            ArtboardSize = artboardSize;
            FloorplanSize = floorplanSize;
            FlipY = flipY;
            RotationRad = rotationDeg * (float)Math.PI / 180.0f;
        }

        /// <summary>Set source coordinate bounds and calculate transformation.</summary>
        public void SetBounds(Bounds bounds)
        {
            _bounds = bounds;

            if (bounds.Width <= 0 || bounds.Height <= 0)
            {
                _scaleX = 1.0f;
                _scaleY = 1.0f;
                _offsetX = Margin;
                _offsetY = Margin;
                return;
            }

            // Calculate scale factors based on mode
            switch (Mode)
            {
                case ScaleMode.Stretch:
                    _scaleX = FloorplanSize / bounds.Width;
                    _scaleY = FloorplanSize / bounds.Height;
                    break;
                case ScaleMode.FitWidth:
                    _scaleX = _scaleY = FloorplanSize / bounds.Width;
                    break;
                case ScaleMode.FitHeight:
                    _scaleX = _scaleY = FloorplanSize / bounds.Height;
                    break;
                case ScaleMode.FitContain:
                    var scaleContain = Math.Min(
                        FloorplanSize / bounds.Width,
                        FloorplanSize / bounds.Height
                    );
                    _scaleX = _scaleY = scaleContain;
                    break;
                case ScaleMode.FitCover:
                    var scaleCover = Math.Max(
                        FloorplanSize / bounds.Width,
                        FloorplanSize / bounds.Height
                    );
                    _scaleX = _scaleY = scaleCover;
                    break;
            }

            // Calculate offsets to center content
            var scaledWidth = bounds.Width * _scaleX;
            var scaledHeight = bounds.Height * _scaleY;
            _offsetX = (ArtboardSize - scaledWidth) / 2.0f;
            _offsetY = (ArtboardSize - scaledHeight) / 2.0f;
        }

        /// <summary>Transform a single coordinate pair.</summary>
        public TransformResult Transform(float x, float y)
        {
            if (_bounds == null)
                throw new InvalidOperationException("Bounds not set. Call SetBounds() first.");

            // Apply rotation if needed
            if (Math.Abs(RotationRad) > 0.001f)
            {
                var (cx, cy) = _bounds.Center;
                var dx = x - cx;
                var dy = y - cy;
                var cosR = (float)Math.Cos(RotationRad);
                var sinR = (float)Math.Sin(RotationRad);
                x = cx + dx * cosR - dy * sinR;
                y = cy + dx * sinR + dy * cosR;
            }

            // Normalize to bounds origin
            var normX = x - _bounds.MinX;
            var normY = y - _bounds.MinY;

            // Scale to artboard
            var artX = _offsetX + normX * _scaleX;
            float artY;

            if (FlipY)
            {
                var normYFlipped = _bounds.Height - normY;
                artY = _offsetY + normYFlipped * _scaleY;
            }
            else
            {
                artY = _offsetY + normY * _scaleY;
            }

            // Convert to SiteOwl (0-100)
            var siteX = (float)Math.Round(artX / 10.0, 2);
            var siteY = (float)Math.Round(artY / 10.0, 2);

            // Check bounds
            var inBounds = artX >= 0 && artX <= ArtboardSize &&
                           artY >= 0 && artY <= ArtboardSize;

            // Calculate confidence
            var confidence = 1.0f;
            if (!inBounds)
            {
                var dist = (float)Math.Sqrt(
                    Math.Pow(artX - ArtboardSize / 2.0, 2) +
                    Math.Pow(artY - ArtboardSize / 2.0, 2)
                );
                var maxDist = ArtboardSize * (float)Math.Sqrt(2) / 2.0f;
                confidence = Math.Max(0.0f, 1.0f - (dist / maxDist - 0.7f) * 2);
            }

            return new TransformResult
            {
                ArtX = artX,
                ArtY = artY,
                SiteX = siteX,
                SiteY = siteY,
                InBounds = inBounds,
                Confidence = confidence
            };
        }

        /// <summary>Transform multiple points at once.</summary>
        public List<TransformResult> TransformBatch(List<(float x, float y)> points)
        {
            var results = new List<TransformResult>();
            foreach (var (x, y) in points)
            {
                results.Add(Transform(x, y));
            }
            return results;
        }

        /// <summary>Convert SiteOwl coordinates back to source coordinates.</summary>
        public (float x, float y) InverseTransform(float siteX, float siteY)
        {
            if (_bounds == null)
                throw new InvalidOperationException("Bounds not set.");

            var artX = siteX * 10.0f;
            var artY = siteY * 10.0f;

            var normX = (artX - _offsetX) / _scaleX;
            float normY;

            if (FlipY)
            {
                var normYFlipped = (artY - _offsetY) / _scaleY;
                normY = _bounds.Height - normYFlipped;
            }
            else
            {
                normY = (artY - _offsetY) / _scaleY;
            }

            var sourceX = normX + _bounds.MinX;
            var sourceY = normY + _bounds.MinY;

            return (sourceX, sourceY);
        }

        /// <summary>Get the 3x3 affine transformation matrix.</summary>
        public float[,] GetTransformMatrix()
        {
            if (_bounds == null)
                return new float[,] {{1, 0, 0}, {0, 1, 0}, {0, 0, 1}};

            var tx1 = -_bounds.MinX;
            var ty1 = -_bounds.MinY;

            var sx = _scaleX;
            var sy = FlipY ? -_scaleY : _scaleY;

            var tx2 = _offsetX;
            var ty2 = FlipY 
                ? _offsetY + _bounds.Height * _scaleY 
                : _offsetY;

            return new float[,]
            {
                {sx, 0, sx * tx1 + tx2},
                {0, sy, sy * ty1 + ty2},
                {0, 0, 1}
            };
        }

        /// <summary>Export configuration as dictionary.</summary>
        public Dictionary<string, object> ToConfigDict()
        {
            var matrix = GetTransformMatrix();
            var matrixList = new List<List<float>>();
            for (int i = 0; i < 3; i++)
            {
                matrixList.Add(new List<float> { matrix[i, 0], matrix[i, 1], matrix[i, 2] });
            }

            return new Dictionary<string, object>
            {
                {"mode", Mode.ToString()},
                {"artboard_size", ArtboardSize},
                {"floorplan_size", FloorplanSize},
                {"flip_y", FlipY},
                {"rotation_deg", RotationRad * 180.0f / (float)Math.PI},
                {"bounds", _bounds?.ToDict()},
                {"matrix", matrixList}
            };
        }
    }

    /// <summary>Convenience methods for quick transforms.</summary>
    public static class TransformUtils
    {
        /// <summary>Quick transform of points to SiteOwl coordinates.</summary>
        public static List<(float siteX, float siteY)> TransformPoints(
            List<(float x, float y)> points,
            ScaleMode mode = ScaleMode.FitContain)
        {
            if (points == null || points.Count == 0)
                return new List<(float, float)>();

            var bounds = Bounds.FromPoints(points);
            if (bounds == null)
                return new List<(float, float)>();

            var transformer = new CoordinateTransformer(mode);
            transformer.SetBounds(bounds);

            var results = new List<(float, float)>();
            foreach (var result in transformer.TransformBatch(points))
            {
                results.Add((result.SiteX, result.SiteY));
            }
            return results;
        }
    }
}
