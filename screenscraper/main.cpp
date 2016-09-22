#include <windows.h>
#include <iostream>
#include <tchar.h>
#include <Strsafe.h>
#include <WinSock.h>
#include <stdio.h>
#include <conio.h>
//#include <vector>



PBITMAPINFO CreateBitmapInfoStruct(HBITMAP hBmp)
{ 
    BITMAP bmp; 
    PBITMAPINFO pbmi; 
    WORD    cClrBits; 

    // Retrieve the bitmap color format, width, and height.  
    if (!GetObject(hBmp, sizeof(BITMAP), (LPSTR)&bmp)) 
	{
        std::cout << "GetObject Failed" << std::endl; 
	}
    // Convert the color format to a count of bits.  
    cClrBits = (WORD)(bmp.bmPlanes * bmp.bmBitsPixel); 
    if (cClrBits == 1) 
        cClrBits = 1; 
    else if (cClrBits <= 4) 
        cClrBits = 4; 
    else if (cClrBits <= 8) 
        cClrBits = 8; 
    else if (cClrBits <= 16) 
        cClrBits = 16; 
    else if (cClrBits <= 24) 
        cClrBits = 24; 
    else cClrBits = 32; 

    // Allocate memory for the BITMAPINFO structure. (This structure  
    // contains a BITMAPINFOHEADER structure and an array of RGBQUAD  
    // data structures.)  

     if (cClrBits < 24) 
         pbmi = (PBITMAPINFO) LocalAlloc(LPTR, 
                    sizeof(BITMAPINFOHEADER) + 
                    sizeof(RGBQUAD) * (1<< cClrBits)); 

     // There is no RGBQUAD array for these formats: 24-bit-per-pixel or 32-bit-per-pixel 

     else 
         pbmi = (PBITMAPINFO) LocalAlloc(LPTR, 
                    sizeof(BITMAPINFOHEADER)); 

    // Initialize the fields in the BITMAPINFO structure.  

    pbmi->bmiHeader.biSize = sizeof(BITMAPINFOHEADER); 
    pbmi->bmiHeader.biWidth = bmp.bmWidth; 
    pbmi->bmiHeader.biHeight = bmp.bmHeight; 
    pbmi->bmiHeader.biPlanes = bmp.bmPlanes; 
    pbmi->bmiHeader.biBitCount = bmp.bmBitsPixel; 
    if (cClrBits < 24) 
        pbmi->bmiHeader.biClrUsed = (1<<cClrBits); 

    // If the bitmap is not compressed, set the BI_RGB flag.  
    pbmi->bmiHeader.biCompression = BI_RGB; 

    // Compute the number of bytes in the array of color  
    // indices and store the result in biSizeImage.  
    // The width must be DWORD aligned unless the bitmap is RLE 
    // compressed. 
    pbmi->bmiHeader.biSizeImage = ((pbmi->bmiHeader.biWidth * cClrBits +31) & ~31) /8
                                  * pbmi->bmiHeader.biHeight; 
    // Set biClrImportant to 0, indicating that all of the  
    // device colors are important.  
     pbmi->bmiHeader.biClrImportant = 0; 
     return pbmi; 
 } 

void CreateBMPFile(LPTSTR pszFile, PBITMAPINFO pbi, HBITMAP hBMP, HDC hDC) 
{ 
	HANDLE hf;                 // file handle  
	BITMAPFILEHEADER hdr;       // bitmap file-header  
	PBITMAPINFOHEADER pbih;     // bitmap info-header  
	LPBYTE lpBits;              // memory pointer  
	DWORD dwTotal;              // total count of bytes  
	DWORD cb;                   // incremental count of bytes  
	BYTE *hp;                   // byte pointer  
	DWORD dwTmp; 

	pbih = (PBITMAPINFOHEADER) pbi; 
	lpBits = (LPBYTE) GlobalAlloc(GMEM_FIXED, pbih->biSizeImage);

	if (!lpBits) 
	{
		std::cout << "GlobalAlloc Failed" << std::endl; 
		return;
	}
	// Retrieve the color table (RGBQUAD array) and the bits  
	// (array of palette indices) from the DIB.  
	if (!GetDIBits(hDC, hBMP, 0, (WORD) pbih->biHeight, lpBits, pbi, 
		DIB_RGB_COLORS)) 
	{
		std::cout << "GetDIBits Failed" << std::endl;
		return;
	}

	// Create the .BMP file.  
	hf = CreateFile(pszFile, 
		GENERIC_READ | GENERIC_WRITE, 
		(DWORD) 0, 
		NULL, 
		CREATE_ALWAYS, 
		FILE_ATTRIBUTE_NORMAL, 
		(HANDLE) NULL); 
	if (hf == INVALID_HANDLE_VALUE) 
	{
		std::cout << "CreateFile Failed" << std::endl;
		return;
	}
	hdr.bfType = 0x4d42;        // 0x42 = "B" 0x4d = "M"  
	// Compute the size of the entire file.  
	hdr.bfSize = (DWORD) (sizeof(BITMAPFILEHEADER) + 
		pbih->biSize + pbih->biClrUsed 
		* sizeof(RGBQUAD) + pbih->biSizeImage); 
	hdr.bfReserved1 = 0; 
	hdr.bfReserved2 = 0; 

	// Compute the offset to the array of color indices.  
	hdr.bfOffBits = (DWORD) sizeof(BITMAPFILEHEADER) + 
		pbih->biSize + pbih->biClrUsed 
		* sizeof (RGBQUAD); 

	// Copy the BITMAPFILEHEADER into the .BMP file.  
	if (!WriteFile(hf, (LPVOID) &hdr, sizeof(BITMAPFILEHEADER), 
		(LPDWORD) &dwTmp,  NULL)) 
	{
		std::cout << "WriteFile Failed" << std::endl;
		return;
	}

	// Copy the BITMAPINFOHEADER and RGBQUAD array into the file.  
	if (!WriteFile(hf, (LPVOID) pbih, sizeof(BITMAPINFOHEADER) 
		+ pbih->biClrUsed * sizeof (RGBQUAD), 
		(LPDWORD) &dwTmp, ( NULL)))
	{
		std::cout << "WriteFile Failed" << std::endl; 
		return;
	}

	// Copy the array of color indices into the .BMP file.  
	dwTotal = cb = pbih->biSizeImage; 
	hp = lpBits; 
	if (!WriteFile(hf, (LPSTR) hp, (int) cb, (LPDWORD) &dwTmp,NULL)) 
	{
		std::cout << "WriteFile Failed" << std::endl; 
		return;
	}

	// Close the .BMP file.  
	if (!CloseHandle(hf)) 
	{
		std::cout << "CloseHandle Failed" << std::endl; 
		return;
	}
	
	// Free memory. 
	GlobalFree((HGLOBAL)lpBits);
}


void CreateBMPFile2(PBITMAPINFO pbi, HBITMAP hBMP, HDC hDC, HANDLE SE, HANDLE CE) 
{ 
	
	BITMAPFILEHEADER hdr;       // bitmap file-header  
	PBITMAPINFOHEADER pbih;     // bitmap info-header  
	LPBYTE lpBits;              // memory pointer  
	DWORD dwTotal;              // total count of bytes  
	DWORD cb;                   // incremental count of bytes  
	BYTE *hp;                   // byte pointer  
	DWORD dwTmp; 

	//std::vector<unsigned char> data; // vector to store image data
	//std::vector<unsigned char>::iterator it;
	//it = data.begin();
	//unsigned char data[10000000];
	unsigned char * data = (unsigned char *) malloc(10000000);
	int it = 0;

	pbih = (PBITMAPINFOHEADER) pbi; 
	lpBits = (LPBYTE) GlobalAlloc(GMEM_FIXED, pbih->biSizeImage);

	if (!lpBits) 
	{
		std::cout << "GlobalAlloc Failed" << std::endl; 
		return;
	}
	// Retrieve the color table (RGBQUAD array) and the bits  
	// (array of palette indices) from the DIB.  
	if (!GetDIBits(hDC, hBMP, 0, (WORD) pbih->biHeight, lpBits, pbi, 
		DIB_RGB_COLORS)) 
	{
		std::cout << "GetDIBits Failed" << std::endl;
		return;
	}

	hdr.bfType = 0x4d42;        // 0x42 = "B" 0x4d = "M"  
	// Compute the size of the entire file.  
	hdr.bfSize = (DWORD) (sizeof(BITMAPFILEHEADER) + 
		pbih->biSize + pbih->biClrUsed 
		* sizeof(RGBQUAD) + pbih->biSizeImage); 
	hdr.bfReserved1 = 0; 
	hdr.bfReserved2 = 0; 

	// Compute the offset to the array of color indices.  
	hdr.bfOffBits = (DWORD) sizeof(BITMAPFILEHEADER) + 
		pbih->biSize + pbih->biClrUsed 
		* sizeof (RGBQUAD); 

	// Copy the BITMAPFILEHEADER into the .BMP file.  
	/*
	if (!WriteFile(hf, (LPVOID) &hdr, sizeof(BITMAPFILEHEADER), 
		(LPDWORD) &dwTmp,  NULL)) 
	{
		std::cout << "WriteFile Failed" << std::endl;
		return;
	}
	*/

	// Write BITMAPFILEHEADER to vector
	//data.insert(data.end(), &hdr, &hdr + sizeof(BITMAPFILEHEADER));
	memcpy(data, &hdr, sizeof(BITMAPFILEHEADER));
	it += sizeof(BITMAPFILEHEADER);


	// Copy the BITMAPINFOHEADER and RGBQUAD array into the file.  
	/*
	if (!WriteFile(hf, (LPVOID) pbih, sizeof(BITMAPINFOHEADER) 
		+ pbih->biClrUsed * sizeof (RGBQUAD), 
		(LPDWORD) &dwTmp, ( NULL)))
	{
		std::cout << "WriteFile Failed" << std::endl; 
		return;
	}
	*/

	// Write BITMAPINFOHEADER to vector
	//data.insert(data.end(), pbih, pbih + sizeof(BITMAPINFOHEADER));
	memcpy(data+it, pbih, sizeof(BITMAPINFOHEADER));
	it += sizeof(BITMAPINFOHEADER);


	// Copy the array of color indices into the .BMP file.  
	dwTotal = cb = pbih->biSizeImage; 
	hp = lpBits; 
	/*
	if (!WriteFile(hf, (LPSTR) hp, (int) cb, (LPDWORD) &dwTmp,NULL)) 
	{
		std::cout << "WriteFile Failed" << std::endl; 
		return;
	}
	*/

	// Write array of color indices to vector
	//data.insert(data.end(), hp, hp + (int) cb);
	if(it + cb >= 10000000)
	{
		std::cout << "Image too big" << std::endl;
		return;
	}
		
	memcpy(data+it, hp, cb);

	// Close the .BMP file.
	/*
	if (!CloseHandle(hf)) 
	{
		std::cout << "CloseHandle Failed" << std::endl; 
		return;
	}
	*/

	TCHAR szName[]=TEXT("ImageMap");

	HANDLE hMapFile;
    LPCTSTR pBuf;
    HANDLE myEvent, theirEvent;

    hMapFile = CreateFileMapping(
                 INVALID_HANDLE_VALUE,    // use paging file
                 NULL,                    // default security
                 PAGE_READWRITE,          // read/write access
                 0,                       // maximum object size (high-order DWORD)
                 10000000,                // maximum object size (low-order DWORD)
                 szName);                 // name of mapping object


	if (hMapFile == NULL)
    {
		_tprintf(TEXT("Could not create file mapping object (%d).\n"),
             GetLastError());
		std::cout << "Error 1" << std::endl;
		return;
    }
    pBuf = (LPTSTR) MapViewOfFile(hMapFile,   // handle to map object
                        FILE_MAP_ALL_ACCESS, // read/write permission
                        0,
                        0,
                        10000000);

    if (pBuf == NULL)
    {
		_tprintf(TEXT("Could not map view of file (%d).\n"),
             GetLastError());

        CloseHandle(hMapFile);
	    std::cout << "Error 2" << std::endl;
        return;
    }

	
	CopyMemory((PVOID)pBuf, data, 10000000 * sizeof(unsigned char));
	SetEvent(SE);
	int rt = WaitForSingleObject(CE, -1);
	//_getch();

	UnmapViewOfFile(pBuf);

	CloseHandle(hMapFile);

	
	// Free memory. 
	free(data);
	GlobalFree((HGLOBAL)lpBits);
}

void save(HBITMAP hBmp, HDC hDC, int i)
{
	TCHAR buf[10];
	//_itot(i, buf, 10);
	_stprintf(buf, TEXT("%d"), i);
	TCHAR out[50] = TEXT("C:\\Users\\richard\\svn\\win\\client-read\\im");
	StringCchCat(out, 50, buf);
	StringCchCat(out, 50, TEXT(".png"));

	PBITMAPINFO pbit = CreateBitmapInfoStruct(hBmp);
	LPTSTR pszFile = out;
	CreateBMPFile(pszFile, pbit, hBmp, hDC);
	
}

int shared_send(HBITMAP hBmp, HDC hDC, HANDLE SE, HANDLE CE)
{
	PBITMAPINFO pbit = CreateBitmapInfoStruct(hBmp);
	CreateBMPFile2(pbit, hBmp, hDC, SE, CE);

	return 0;
}

void main()
{
	/*
    int nScreenWidth = GetSystemMetrics(SM_CXSCREEN);
    int nScreenHeight = GetSystemMetrics(SM_CYSCREEN);
    HWND hDesktopWnd = GetDesktopWindow();
    HDC hDesktopDC = GetDC(hDesktopWnd);
    HDC hCaptureDC = CreateCompatibleDC(hDesktopDC);
    HBITMAP hCaptureBitmap =CreateCompatibleBitmap(hDesktopDC, 
                            nScreenWidth, nScreenHeight);
    SelectObject(hCaptureDC,hCaptureBitmap); 
    BitBlt(hCaptureDC,0,0,nScreenWidth,nScreenHeight,
           hDesktopDC,0,0,SRCCOPY|CAPTUREBLT); 

	save(hCaptureBitmap, hCaptureDC);

    
    ReleaseDC(hDesktopWnd,hDesktopDC);
    DeleteDC(hCaptureDC);
    DeleteObject(hCaptureBitmap);
}
   */	

	RECT rc;
	HWND hwnd;
	HDC hdcScreen;
	HDC hdc;
	HBITMAP hbmp;
	int i = 0;
	struct _FILETIME ftime; 
	GetSystemTimeAsFileTime(&ftime);
	ULONGLONG last = (((ULONGLONG) ftime.dwHighDateTime) << 32) + ftime.dwLowDateTime;
	ULONGLONG current;
	int diff;
	HANDLE ServerEvent, ClientEvent;

	//ServerEvent = CreateEvent(NULL, FALSE, FALSE, TEXT("ServerEvent"));
	//ClientEvent = CreateEvent(NULL, FALSE, FALSE, TEXT("ClientEvent"));

	ServerEvent = OpenEvent(EVENT_ALL_ACCESS, FALSE, TEXT("ServerEvent"));
	ClientEvent = OpenEvent(SYNCHRONIZE, FALSE, TEXT("ClientEvent"));

	while(1)
	{
		i++;
		hwnd = FindWindow(NULL, TEXT("▶ Testing - YouTube - Mozilla Firefox"));    //the window can't be min
		hwnd = FindWindow(NULL, TEXT("Testing - YouTube - Mozilla Firefox"));    //the window can't be min
		//hwnd = FindWindow(NULL, TEXT("Free Live Streaming Service | Ad-Free Live Video Hosting - Mozilla Firefox"));    //the window can't be min
		//hwnd = FindWindow(NULL, TEXT("Facebook - Mozilla Firefox"));
		//hwnd = FindWindow(NULL, TEXT("ConnectCast - Google Chrome"));
		//hwnd = FindWindow(NULL, TEXT("ConnectCast - Mozilla Firefox"));
		//hwnd = FindWindow(NULL, TEXT("Adobe Flash Player"));
		if (hwnd == NULL)
		{
			std::cout << "cannot find the desired window" << std::endl;
			return;
		}

		// Get hwnd coordinates and put in rc
		GetClientRect(hwnd, &rc);

		// Get DC for entire screen
		hdcScreen = GetDC(NULL);

		// Creates device context for input
		hdc = CreateCompatibleDC(hdcScreen);
		
		// Creates bitmap compatible with given dc
		hbmp = CreateCompatibleBitmap(hdcScreen, rc.right - rc.left, rc.bottom - rc.top);
		
		// Puts Object into specified dc
		SelectObject(hdc, hbmp);

		// Copies visual windos into specific dc
		PrintWindow(hwnd, hdc, PW_CLIENTONLY);

		if(shared_send(hbmp, hdc, ServerEvent, ClientEvent))
			break;

		//save(hbmp, hdc, i);
		//std::cout << i << std::endl;

		DeleteObject(hbmp);
		DeleteDC(hdc);//ReleaseDC(hwnd,hdc);
		DeleteDC(hdcScreen);

		GetSystemTimeAsFileTime(&ftime);
		current = (((ULONGLONG) ftime.dwHighDateTime) << 32) + ftime.dwLowDateTime;
		diff = (int)((current-last)/10000);
		if (diff >= 150) //cc:150 yt:200
			std::cout << diff << std::endl;
		int wait_time = 100; // cc:100 yt:150
		if (diff < wait_time)
		{
			Sleep(wait_time-diff);
		}
		last = current;
		//Sleep(300);
		//Sleep(165);
	}
}