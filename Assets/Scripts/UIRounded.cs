using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

/// <summary>
/// Gives a UI Image rounded corners, a pill shape, or an outline only, with no image files needed.
/// Add it to anything that has an Image (buttons, panels, the hint card, the band chip and dot),
/// then set the colour on the Image as usual. Works in the Editor and on the phone.
///
///   Radius        corner radius in canvas pixels (cards: 32 to 48)
///   Pill          fully round ends, radius = half the height (chips, pill buttons, dots)
///   Outline Only  just the border, for secondary buttons like "Set zero"
/// </summary>
[ExecuteAlways]
[RequireComponent(typeof(Image))]
public class UIRounded : MonoBehaviour
{
    [Tooltip("Corner radius in canvas pixels. Ignored when Pill is ticked.")]
    [SerializeField] float radius = 32f;

    [Tooltip("Fully round ends: the radius becomes half the height. Use for chips, pill buttons and dots.")]
    [SerializeField] bool pill = false;

    [Tooltip("Draw only the border, for secondary buttons.")]
    [SerializeField] bool outlineOnly = false;

    [SerializeField] float outlineWidth = 4f;

    static readonly Dictionary<int, Sprite> cache = new Dictionary<int, Sprite>();

    Image image;
    int lastRadius = -1;
    int lastWidth = -1;

    void OnEnable()
    {
        Apply(true);
    }

    void OnRectTransformDimensionsChange()
    {
        if (pill && isActiveAndEnabled)
            Apply(false);
    }

#if UNITY_EDITOR
    void OnValidate()
    {
        // Changing an Image inside OnValidate makes Unity complain, so wait a moment.
        UnityEditor.EditorApplication.delayCall += () =>
        {
            if (this != null && isActiveAndEnabled)
                Apply(true);
        };
    }
#endif

    void Apply(bool force)
    {
        if (image == null)
            image = GetComponent<Image>();
        RectTransform rt = transform as RectTransform;
        if (image == null || rt == null)
            return;

        float r = pill ? Mathf.Min(rt.rect.width, rt.rect.height) * 0.5f : radius;
        int ri = Mathf.Clamp(Mathf.RoundToInt(r), 1, 512);
        int wi = outlineOnly ? Mathf.Clamp(Mathf.RoundToInt(outlineWidth), 1, ri) : 0;
        if (!force && ri == lastRadius && wi == lastWidth)
            return;
        lastRadius = ri;
        lastWidth = wi;

        image.sprite = GetSprite(ri, wi);
        image.type = Image.Type.Sliced;
        image.fillCenter = true;
        image.pixelsPerUnitMultiplier = 1f;
    }

    /// <summary>A white rounded square, sliced so its corners keep their size at any width or height.</summary>
    static Sprite GetSprite(int r, int outline)
    {
        int key = r * 1000 + outline;
        Sprite cached;
        if (cache.TryGetValue(key, out cached) && cached != null)
            return cached;

        int size = r * 2 + 2;
        float half = size * 0.5f;
        float straight = half - r;          // half-length of the straight part (1 pixel)
        Texture2D tex = new Texture2D(size, size, TextureFormat.RGBA32, false);
        tex.wrapMode = TextureWrapMode.Clamp;
        tex.filterMode = FilterMode.Bilinear;
        tex.hideFlags = HideFlags.HideAndDontSave;

        Color32[] pixels = new Color32[size * size];
        for (int y = 0; y < size; y++)
        {
            for (int x = 0; x < size; x++)
            {
                float dx = Mathf.Max(0f, Mathf.Abs(x + 0.5f - half) - straight);
                float dy = Mathf.Max(0f, Mathf.Abs(y + 0.5f - half) - straight);
                float d = Mathf.Sqrt(dx * dx + dy * dy);
                float a = Mathf.Clamp01(r - d + 0.5f);                 // smooth outer edge
                if (outline > 0)
                    a -= Mathf.Clamp01(r - outline - d + 0.5f);        // hollow the middle
                pixels[y * size + x] = new Color32(255, 255, 255, (byte)Mathf.RoundToInt(Mathf.Clamp01(a) * 255f));
            }
        }
        tex.SetPixels32(pixels);
        tex.Apply();

        Sprite sprite = Sprite.Create(tex, new Rect(0, 0, size, size), new Vector2(0.5f, 0.5f),
            100f, 0, SpriteMeshType.FullRect, new Vector4(r, r, r, r));
        sprite.hideFlags = HideFlags.HideAndDontSave;
        cache[key] = sprite;
        return sprite;
    }
}
