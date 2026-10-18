using UnityEngine;

/// <summary>
/// Put this on the Disk. Drag the ring objects into "Rings", innermost or outermost first.
/// For now a UI slider calls SetAngle. Later the wristband's angle will call the same method.
/// </summary>
public class RingController : MonoBehaviour
{
    [SerializeField] Transform[] rings;
    [SerializeField] int selected = 0;

    /// <summary>Index of the ring that currently turns.</summary>
    public int Selected { get { return selected; } }

    /// <summary>The last angle given to SetAngle, in degrees.</summary>
    public float CurrentAngle { get; private set; }

    /// <summary>Turn the selected ring to this angle, in degrees, about the disk's upright axis.</summary>
    public void SetAngle(float degrees)
    {
        CurrentAngle = degrees;
        if (rings == null || rings.Length == 0)
            return;
        rings[selected].localRotation = Quaternion.Euler(0f, degrees, 0f);
    }

    /// <summary>Move on to the next ring. Hook this to a UI button.</summary>
    public void SelectNext()
    {
        if (rings == null || rings.Length == 0)
            return;
        selected = (selected + 1) % rings.Length;
    }
}
