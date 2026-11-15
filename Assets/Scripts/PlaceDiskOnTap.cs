using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;

/// <summary>
/// Put this on the XR Origin (it needs the AR Raycast Manager that sits there).
/// The first tap on a detected surface moves the disk there and shows it.
/// Taps on buttons and other UI are ignored, so pressing "?" never places the disk.
/// </summary>
[RequireComponent(typeof(ARRaycastManager))]
public class PlaceDiskOnTap : MonoBehaviour
{
    [Tooltip("The Disk object in the scene. Leave it switched off (inactive) to start with.")]
    [SerializeField] Transform disk;

    [Tooltip("Optional: the AR Plane Manager on the XR Origin, so the surface outlines can be hidden after placing.")]
    [SerializeField] ARPlaneManager planeManager;

    [SerializeField] bool hidePlanesAfterPlacing = true;

    ARRaycastManager raycastManager;
    static readonly List<ARRaycastHit> hits = new List<ARRaycastHit>();
    static readonly List<RaycastResult> uiHits = new List<RaycastResult>();
    bool placed;

    /// <summary>True once the disk is on a surface.</summary>
    public bool Placed { get { return placed; } }

    void Awake()
    {
        raycastManager = GetComponent<ARRaycastManager>();
    }

    void Update()
    {
        if (placed || disk == null)
            return;

        // Pointer covers a finger on the phone and the mouse in the Editor.
        Pointer pointer = Pointer.current;
        if (pointer == null || !pointer.press.wasPressedThisFrame)
            return;

        Vector2 screenPoint = pointer.position.ReadValue();
        if (IsOverUI(screenPoint))
            return;
        if (!raycastManager.Raycast(screenPoint, hits, TrackableType.PlaneWithinPolygon))
            return;

        Pose pose = hits[0].pose;
        disk.SetPositionAndRotation(pose.position, pose.rotation);
        disk.gameObject.SetActive(true);
        placed = true;

        if (hidePlanesAfterPlacing && planeManager != null)
        {
            foreach (ARPlane plane in planeManager.trackables)
                plane.gameObject.SetActive(false);
            planeManager.enabled = false;
        }
    }

    static bool IsOverUI(Vector2 screenPoint)
    {
        EventSystem events = EventSystem.current;
        if (events == null)
            return false;
        PointerEventData data = new PointerEventData(events);
        data.position = screenPoint;
        uiHits.Clear();
        events.RaycastAll(data, uiHits);
        return uiHits.Count > 0;
    }

    /// <summary>Hook this to a "Move disk" button if you want to place it again.</summary>
    public void ResetPlacement()
    {
        placed = false;
        if (disk != null)
            disk.gameObject.SetActive(false);
        if (planeManager != null)
        {
            planeManager.enabled = true;
            foreach (ARPlane plane in planeManager.trackables)
                plane.gameObject.SetActive(true);
        }
    }
}
